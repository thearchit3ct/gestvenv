"""
Gestionnaire principal des environnements éphémères
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Dict, Optional, List, AsyncIterator
from contextlib import asynccontextmanager

from .models import (
    EphemeralEnvironment,
    EphemeralConfig,
    EphemeralStatus,
    CleanupReason,
    ResourceUsage
)
from .exceptions import (
    ResourceExhaustedException,
    EnvironmentCreationException,
    CleanupException,
    EnvironmentNotFoundException
)
from .lifecycle import LifecycleController
from .monitoring import ResourceTracker
from .cleanup import CleanupScheduler
from .storage import StorageManager

logger = logging.getLogger(__name__)


class EphemeralManager:
    """Gestionnaire principal des environnements éphémères"""
    
    def __init__(self, config: Optional[EphemeralConfig] = None):
        self.config = config or EphemeralConfig()
        self.active_environments: Dict[str, EphemeralEnvironment] = {}
        self._lock = asyncio.Lock()
        self._shutdown = False
        
        # Composants principaux
        self.lifecycle_controller = LifecycleController(self)
        self.resource_tracker = ResourceTracker(self)
        self.cleanup_scheduler = CleanupScheduler(self)
        self.storage_manager = StorageManager(self.config)
        
        # Tâches d'arrière-plan
        self._background_tasks: List[asyncio.Task] = []
    
    async def start(self):
        """Démarrage du gestionnaire"""
        logger.info("Starting EphemeralManager")
        
        # Démarrage des composants
        await self.storage_manager.initialize()
        await self.cleanup_scheduler.start()
        
        if self.config.enable_monitoring:
            await self.resource_tracker.start()
        
        logger.info(f"EphemeralManager started with config: {self.config}")
    
    async def stop(self):
        """Arrêt du gestionnaire"""
        logger.info("Stopping EphemeralManager")
        self._shutdown = True
        
        # Arrêt des tâches d'arrière-plan
        for task in self._background_tasks:
            task.cancel()
        
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        # Nettoyage d'urgence de tous les environnements
        await self.cleanup_scheduler.emergency_cleanup_all()
        
        # Arrêt des composants
        await self.cleanup_scheduler.stop()
        await self.resource_tracker.stop()
        
        logger.info("EphemeralManager stopped")
    
    @asynccontextmanager
    async def create_ephemeral(
        self,
        name: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[EphemeralEnvironment]:
        """Context manager pour environnement éphémère"""
        
        if self._shutdown:
            raise RuntimeError("EphemeralManager is shutting down")
        
        # Validation des limites de ressources
        await self._check_resource_limits()
        
        # Création de l'environnement
        env = await self._create_environment(name, **kwargs)
        
        try:
            # Enregistrement et monitoring
            await self._register_environment(env)
            logger.info(f"Created ephemeral environment: {env.id} ({env.name})")
            yield env
            
        except Exception as e:
            logger.error(f"Error in ephemeral environment {env.id}: {e}")
            await self._emergency_cleanup(env)
            raise
            
        finally:
            # Cleanup automatique garanti
            await self._cleanup_environment(env)
    
    async def get_environment(self, env_id: str) -> EphemeralEnvironment:
        """Récupération d'un environnement par son ID"""
        async with self._lock:
            if env_id not in self.active_environments:
                raise EnvironmentNotFoundException(f"Environment {env_id} not found")
            return self.active_environments[env_id]
    
    async def list_environments(self) -> List[EphemeralEnvironment]:
        """Liste tous les environnements actifs"""
        async with self._lock:
            return list(self.active_environments.values())
    
    async def get_environment_by_name(self, name: str) -> Optional[EphemeralEnvironment]:
        """Récupération d'un environnement par son nom"""
        async with self._lock:
            for env in self.active_environments.values():
                if env.name == name:
                    return env
            return None
    
    async def cleanup_environment(self, env_id: str, force: bool = False) -> bool:
        """Nettoyage manuel d'un environnement"""
        try:
            env = await self.get_environment(env_id)
            await self._cleanup_environment(env, force=force)
            return True
        except EnvironmentNotFoundException:
            return False
    
    async def get_resource_usage(self) -> Dict[str, any]:
        """Récupération de l'usage global des ressources"""
        total_memory = 0
        total_disk = 0
        active_count = 0
        
        async with self._lock:
            for env in self.active_environments.values():
                if env.is_active:
                    active_count += 1
                    if env.peak_memory_mb:
                        total_memory += env.peak_memory_mb
                    if env.peak_disk_mb:
                        total_disk += env.peak_disk_mb
        
        return {
            "active_environments": active_count,
            "total_memory_mb": total_memory,
            "total_disk_mb": total_disk,
            "max_concurrent": self.config.max_concurrent,
            "max_total_memory_mb": self.config.max_total_memory_mb,
            "max_total_disk_mb": self.config.max_total_disk_mb
        }
    
    async def _create_environment(
        self,
        name: Optional[str],
        **kwargs
    ) -> EphemeralEnvironment:
        """Création d'un nouvel environnement"""
        
        # Configuration de l'environnement
        env_config = EphemeralEnvironment(name=name, **kwargs)
        env_config.status = EphemeralStatus.CREATING
        
        creation_start = time.time()
        
        try:
            # Allocation du stockage
            storage_path = await self.storage_manager.allocate_storage(
                env_config.id,
                estimated_size_mb=env_config.resource_limits.max_disk or 1024
            )
            env_config.storage_path = storage_path
            
            # Création par le contrôleur de cycle de vie
            await self.lifecycle_controller.create(env_config)
            
            # Mesure du temps de création
            env_config.creation_time = time.time() - creation_start
            env_config.status = EphemeralStatus.READY
            
            logger.info(
                f"Environment {env_config.id} created in {env_config.creation_time:.2f}s"
            )
            
            return env_config
            
        except Exception as e:
            env_config.status = EphemeralStatus.FAILED
            await self._cleanup_failed_creation(env_config)
            raise EnvironmentCreationException(f"Failed to create environment: {e}")
    
    async def _register_environment(self, env: EphemeralEnvironment):
        """Enregistrement d'un environnement"""
        async with self._lock:
            self.active_environments[env.id] = env
        
        # Démarrage du monitoring si activé
        if self.config.enable_monitoring:
            await self.resource_tracker.start_monitoring(env)
    
    async def _cleanup_environment(
        self,
        env: EphemeralEnvironment,
        force: bool = False
    ):
        """Nettoyage d'un environnement"""
        cleanup_start = time.time()
        
        try:
            env.status = EphemeralStatus.CLEANING_UP
            
            # Arrêt du monitoring
            if self.config.enable_monitoring:
                await self.resource_tracker.stop_monitoring(env.id)
            
            # Nettoyage par le contrôleur de cycle de vie
            await self.lifecycle_controller.cleanup(env, force=force)
            
            # Libération du stockage
            if env.storage_path:
                await self.storage_manager.release_storage(env.storage_path)
            
            # Suppression de la liste active
            async with self._lock:
                if env.id in self.active_environments:
                    del self.active_environments[env.id]
            
            env.cleanup_time = time.time() - cleanup_start
            env.status = EphemeralStatus.DESTROYED
            
            logger.info(
                f"Environment {env.id} cleaned up in {env.cleanup_time:.2f}s"
            )
            
        except Exception as e:
            logger.error(f"Failed to cleanup environment {env.id}: {e}")
            raise CleanupException(f"Cleanup failed: {e}")
    
    async def _emergency_cleanup(self, env: EphemeralEnvironment):
        """Nettoyage d'urgence en cas d'erreur"""
        try:
            await self._cleanup_environment(env, force=True)
        except Exception as e:
            logger.critical(f"Emergency cleanup failed for {env.id}: {e}")
    
    async def _cleanup_failed_creation(self, env: EphemeralEnvironment):
        """Nettoyage après échec de création"""
        try:
            if env.storage_path:
                await self.storage_manager.release_storage(env.storage_path)
        except Exception as e:
            logger.error(f"Failed to cleanup after creation failure: {e}")
    
    async def _check_resource_limits(self):
        """Vérification des limites de ressources globales"""
        async with self._lock:
            active_count = len(self.active_environments)
            
            if active_count >= self.config.max_concurrent:
                # Tentative de nettoyage préventif
                await self.cleanup_scheduler.cleanup_inactive()
                
                # Nouvelle vérification
                active_count = len(self.active_environments)
                if active_count >= self.config.max_concurrent:
                    raise ResourceExhaustedException(
                        f"Maximum concurrent environments reached: {self.config.max_concurrent}"
                    )
        
        # Vérification de l'usage mémoire total
        usage = await self.get_resource_usage()
        
        if usage["total_memory_mb"] > self.config.max_total_memory_mb:
            raise ResourceExhaustedException(
                f"Total memory limit exceeded: {usage['total_memory_mb']}MB > {self.config.max_total_memory_mb}MB"
            )
        
        if usage["total_disk_mb"] > self.config.max_total_disk_mb:
            raise ResourceExhaustedException(
                f"Total disk limit exceeded: {usage['total_disk_mb']}MB > {self.config.max_total_disk_mb}MB"
            )