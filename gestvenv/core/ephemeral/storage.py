"""
Gestionnaire de stockage optimisé pour environnements éphémères
"""

import asyncio
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from .models import EphemeralConfig, StorageBackend
from .exceptions import EphemeralException

logger = logging.getLogger(__name__)


class StorageManager:
    """Gestionnaire de stockage optimisé"""
    
    def __init__(self, config: EphemeralConfig):
        self.config = config
        self.storage_path = config.base_storage_path
        self._initialized = False
    
    async def initialize(self):
        """Initialisation du gestionnaire de stockage"""
        
        if self._initialized:
            return
        
        logger.info(f"Initializing storage manager with backend: {self.config.storage_backend}")
        
        # Création du répertoire de base
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Configuration spécifique selon le backend
        if self.config.storage_backend == StorageBackend.TMPFS:
            await self._setup_tmpfs()
        elif self.config.storage_backend == StorageBackend.MEMORY:
            await self._setup_memory_storage()
        else:
            await self._setup_disk_storage()
        
        self._initialized = True
        logger.info(f"Storage manager initialized at: {self.storage_path}")
    
    async def allocate_storage(
        self,
        env_id: str,
        estimated_size_mb: int = 1024
    ) -> Path:
        """Allocation rapide d'espace de stockage"""
        
        if not self._initialized:
            await self.initialize()
        
        env_path = self.storage_path / env_id
        
        # Création avec optimisations système
        env_path.mkdir(parents=True, exist_ok=True)
        
        # Configuration des permissions restreintes
        os.chmod(env_path, 0o700)
        
        # Pré-allocation d'espace si supporté et activé
        if self.config.enable_preallocation:
            await self._preallocate_space(env_path, estimated_size_mb)
        
        logger.debug(f"Allocated storage for {env_id}: {env_path}")
        return env_path
    
    async def release_storage(self, env_path: Path):
        """Libération de l'espace de stockage"""
        
        if not env_path.exists():
            return
        
        try:
            # Suppression rapide selon le backend
            if self.config.storage_backend == StorageBackend.MEMORY:
                # Suppression immédiate en mémoire
                shutil.rmtree(env_path, ignore_errors=True)
            else:
                # Suppression asynchrone pour éviter le blocage
                await self._async_remove_directory(env_path)
            
            logger.debug(f"Released storage: {env_path}")
            
        except Exception as e:
            logger.error(f"Failed to release storage {env_path}: {e}")
    
    async def get_usage_stats(self) -> dict:
        """Statistiques d'usage du stockage"""
        
        if not self.storage_path.exists():
            return {"total_mb": 0, "used_mb": 0, "available_mb": 0}
        
        try:
            # Utilisation de statvfs pour les statistiques
            statvfs = os.statvfs(self.storage_path)
            
            total_bytes = statvfs.f_frsize * statvfs.f_blocks
            available_bytes = statvfs.f_frsize * statvfs.f_available
            used_bytes = total_bytes - available_bytes
            
            return {
                "total_mb": total_bytes / (1024 * 1024),
                "used_mb": used_bytes / (1024 * 1024),
                "available_mb": available_bytes / (1024 * 1024)
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage usage: {e}")
            return {"total_mb": 0, "used_mb": 0, "available_mb": 0}
    
    async def cleanup_orphaned(self):
        """Nettoyage des répertoires orphelins"""
        
        if not self.storage_path.exists():
            return
        
        logger.info("Cleaning up orphaned storage directories")
        
        try:
            for item in self.storage_path.iterdir():
                if item.is_dir():
                    # Vérification si le répertoire est orphelin
                    # (aucun processus actif, pas de lock file, etc.)
                    if await self._is_orphaned_directory(item):
                        logger.info(f"Removing orphaned directory: {item}")
                        await self._async_remove_directory(item)
        
        except Exception as e:
            logger.error(f"Failed to cleanup orphaned directories: {e}")
    
    async def _setup_tmpfs(self):
        """Configuration du stockage tmpfs"""
        
        # Vérification si tmpfs est disponible
        if not Path("/tmp").exists():
            raise EphemeralException("tmpfs not available")
        
        # Vérification de l'espace disponible
        stats = await self.get_usage_stats()
        if stats["available_mb"] < 1024:  # Minimum 1GB
            logger.warning(f"Low tmpfs space available: {stats['available_mb']:.1f}MB")
    
    async def _setup_memory_storage(self):
        """Configuration du stockage en mémoire pure"""
        
        # Vérification si /dev/shm est disponible
        if not Path("/dev/shm").exists():
            raise EphemeralException("/dev/shm not available for memory storage")
        
        # Configuration du répertoire en mémoire
        shm_path = Path("/dev/shm") / "gestvenv-ephemeral"
        shm_path.mkdir(parents=True, exist_ok=True)
        self.storage_path = shm_path
    
    async def _setup_disk_storage(self):
        """Configuration du stockage disque standard"""
        
        # Création du répertoire avec permissions appropriées
        self.storage_path.mkdir(parents=True, exist_ok=True)
        os.chmod(self.storage_path, 0o755)
    
    async def _preallocate_space(self, env_path: Path, size_mb: int):
        """Pré-allocation d'espace disque"""
        
        try:
            # Création d'un fichier de pré-allocation
            preallocate_file = env_path / ".preallocate"
            
            if hasattr(os, 'posix_fallocate'):
                # Utilisation de posix_fallocate si disponible (Linux)
                fd = os.open(preallocate_file, os.O_CREAT | os.O_WRONLY)
                try:
                    os.posix_fallocate(fd, 0, size_mb * 1024 * 1024)
                finally:
                    os.close(fd)
            else:
                # Fallback: création d'un fichier sparse
                with open(preallocate_file, 'wb') as f:
                    f.seek(size_mb * 1024 * 1024 - 1)
                    f.write(b'\0')
            
            logger.debug(f"Preallocated {size_mb}MB for {env_path}")
            
        except OSError as e:
            # Pré-allocation échouée, mais pas critique
            logger.debug(f"Preallocation failed (non-critical): {e}")
    
    async def _async_remove_directory(self, path: Path):
        """Suppression asynchrone d'un répertoire"""
        
        def remove_sync():
            if path.exists():
                shutil.rmtree(path, ignore_errors=True)
        
        # Exécution dans un thread pour éviter le blocage
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, remove_sync)
    
    async def _is_orphaned_directory(self, path: Path) -> bool:
        """Vérification si un répertoire est orphelin"""
        
        try:
            # Vérification de l'âge du répertoire
            import time
            stat = path.stat()
            age_hours = (time.time() - stat.st_mtime) / 3600
            
            # Considéré orphelin si plus de 2 heures et pas de processus actif
            if age_hours > 2:
                # Vérification simple: absence de fichiers de lock
                lock_files = list(path.glob("*.lock"))
                if not lock_files:
                    return True
            
            return False
            
        except Exception:
            # En cas de doute, ne pas supprimer
            return False


class FastEnvironmentFactory:
    """Factory optimisée pour création rapide d'environnements"""
    
    def __init__(self, storage_manager: StorageManager):
        self.storage_manager = storage_manager
        self._template_cache: dict = {}
        self._ready_pool = asyncio.Queue(maxsize=5)
        self._pool_task: Optional[asyncio.Task] = None
    
    async def start_pool_maintenance(self):
        """Démarrage de la maintenance du pool"""
        if self._pool_task is None:
            self._pool_task = asyncio.create_task(self._maintain_ready_pool())
    
    async def stop_pool_maintenance(self):
        """Arrêt de la maintenance du pool"""
        if self._pool_task:
            self._pool_task.cancel()
            try:
                await self._pool_task
            except asyncio.CancelledError:
                pass
            self._pool_task = None
    
    async def get_or_create_fast(self, env: 'EphemeralEnvironment') -> 'EphemeralEnvironment':
        """Récupération ultra-rapide d'environnement"""
        
        # Tentative de récupération depuis le pool
        try:
            pooled_env = self._ready_pool.get_nowait()
            return await self._configure_pooled_environment(pooled_env, env)
        except asyncio.QueueEmpty:
            pass
        
        # Création depuis template en cache
        template_key = f"{env.python_version}-{env.backend.value}"
        if template_key in self._template_cache:
            return await self._create_from_template(env, template_key)
        
        # Création complète (plus lente)
        return await self._create_full_environment(env)
    
    async def _maintain_ready_pool(self):
        """Maintenance du pool d'environnements prêts"""
        
        while True:
            try:
                if self._ready_pool.qsize() < 3:
                    # Pré-création d'environnements de base
                    env = await self._create_template_environment()
                    await self._ready_pool.put(env)
                
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Pool maintenance error: {e}")
                await asyncio.sleep(60)
    
    async def _create_template_environment(self):
        """Création d'un environnement template pour le pool"""
        # TODO: Implémentation en Phase 3
        pass
    
    async def _configure_pooled_environment(self, pooled_env, target_env):
        """Configuration rapide d'un environnement du pool"""
        # TODO: Implémentation en Phase 3
        pass
    
    async def _create_from_template(self, env, template_key):
        """Création depuis un template mis en cache"""
        # TODO: Implémentation en Phase 3
        pass
    
    async def _create_full_environment(self, env):
        """Création complète d'un environnement (fallback)"""
        # TODO: Implémentation en Phase 3
        pass