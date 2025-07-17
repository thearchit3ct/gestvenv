"""
Monitoring et suivi des ressources pour environnements éphémères
"""

import asyncio
import logging
import psutil
import time
from pathlib import Path
from typing import Dict, Optional, List

from .models import (
    EphemeralEnvironment,
    ResourceUsage,
    EphemeralStatus
)
from .exceptions import EphemeralException

logger = logging.getLogger(__name__)


class ResourceTracker:
    """Suivi des ressources en temps réel"""
    
    def __init__(self, manager):
        self.manager = manager
        self.monitoring_task: Optional[asyncio.Task] = None
        self.resource_history: Dict[str, List[ResourceUsage]] = {}
        self._shutdown = False
    
    async def start(self):
        """Démarrage du monitoring"""
        if self.monitoring_task is None:
            logger.info("Starting resource monitoring")
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop(self):
        """Arrêt du monitoring"""
        self._shutdown = True
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
        logger.info("Resource monitoring stopped")
    
    async def start_monitoring(self, env: EphemeralEnvironment):
        """Démarrage du monitoring pour un environnement spécifique"""
        if env.id not in self.resource_history:
            self.resource_history[env.id] = []
        logger.debug(f"Started monitoring for environment {env.id}")
    
    async def stop_monitoring(self, env_id: str):
        """Arrêt du monitoring pour un environnement"""
        if env_id in self.resource_history:
            # Conservation de l'historique pendant un court moment
            history = self.resource_history[env_id]
            if history:
                logger.debug(f"Stopped monitoring for {env_id}, peak memory: {max(r.memory_mb for r in history):.1f}MB")
            del self.resource_history[env_id]
    
    async def get_current_usage(self, env: EphemeralEnvironment) -> Optional[ResourceUsage]:
        """Récupération de l'usage actuel d'un environnement"""
        try:
            return await self._measure_environment_resources(env)
        except Exception as e:
            logger.warning(f"Failed to get usage for {env.id}: {e}")
            return None
    
    async def get_resource_history(self, env_id: str) -> List[ResourceUsage]:
        """Récupération de l'historique des ressources"""
        return self.resource_history.get(env_id, [])
    
    async def _monitoring_loop(self):
        """Boucle principale de monitoring"""
        while not self._shutdown:
            try:
                # Monitoring de tous les environnements actifs
                environments = await self.manager.list_environments()
                
                for env in environments:
                    if env.is_active and env.id in self.resource_history:
                        usage = await self._measure_environment_resources(env)
                        if usage:
                            await self._record_usage(env, usage)
                
                # Nettoyage de l'historique ancien
                await self._cleanup_old_history()
                
                # Attente avant la prochaine mesure
                await asyncio.sleep(self.manager.config.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(30)  # Attente plus longue en cas d'erreur
    
    async def _measure_environment_resources(self, env: EphemeralEnvironment) -> Optional[ResourceUsage]:
        """Mesure des ressources d'un environnement"""
        try:
            # Mesure de l'usage disque
            disk_usage_mb = 0.0
            if env.storage_path and env.storage_path.exists():
                disk_usage_mb = await self._get_directory_size(env.storage_path)
            
            # Mesure de l'usage mémoire et CPU
            memory_mb = 0.0
            cpu_percent = 0.0
            active_processes = 0
            
            if env.pid:
                try:
                    # Processus principal
                    main_process = psutil.Process(env.pid)
                    if main_process.is_running():
                        memory_mb += main_process.memory_info().rss / (1024 * 1024)
                        cpu_percent += main_process.cpu_percent()
                        active_processes += 1
                        
                        # Processus enfants
                        for child in main_process.children(recursive=True):
                            try:
                                if child.is_running():
                                    memory_mb += child.memory_info().rss / (1024 * 1024)
                                    cpu_percent += child.cpu_percent()
                                    active_processes += 1
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                continue
                                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Processus terminé ou accès refusé
                    pass
            
            return ResourceUsage(
                memory_mb=memory_mb,
                disk_mb=disk_usage_mb,
                cpu_percent=cpu_percent,
                active_processes=active_processes
            )
            
        except Exception as e:
            logger.warning(f"Failed to measure resources for {env.id}: {e}")
            return None
    
    async def _get_directory_size(self, path: Path) -> float:
        """Calcul de la taille d'un répertoire en MB"""
        try:
            def get_size():
                total_size = 0
                for dirpath, dirnames, filenames in path.walk():
                    for filename in filenames:
                        try:
                            file_path = dirpath / filename
                            total_size += file_path.stat().st_size
                        except (OSError, FileNotFoundError):
                            continue
                return total_size / (1024 * 1024)  # Conversion en MB
            
            # Exécution dans un thread pour éviter le blocage
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, get_size)
            
        except Exception:
            return 0.0
    
    async def _record_usage(self, env: EphemeralEnvironment, usage: ResourceUsage):
        """Enregistrement d'une mesure d'usage"""
        # Ajout à l'historique
        if env.id in self.resource_history:
            self.resource_history[env.id].append(usage)
            
            # Limitation de la taille de l'historique (30 dernières mesures)
            if len(self.resource_history[env.id]) > 30:
                self.resource_history[env.id] = self.resource_history[env.id][-30:]
        
        # Mise à jour des pics dans l'environnement
        if env.peak_memory_mb is None or usage.memory_mb > env.peak_memory_mb:
            env.peak_memory_mb = usage.memory_mb
        
        if env.peak_disk_mb is None or usage.disk_mb > env.peak_disk_mb:
            env.peak_disk_mb = usage.disk_mb
        
        # Vérification des limites
        await self._check_resource_limits(env, usage)
    
    async def _check_resource_limits(self, env: EphemeralEnvironment, usage: ResourceUsage):
        """Vérification des limites de ressources"""
        limits = env.resource_limits
        
        # Vérification mémoire
        if limits.max_memory and usage.memory_mb > limits.max_memory:
            logger.warning(
                f"Environment {env.id} exceeded memory limit: "
                f"{usage.memory_mb:.1f}MB > {limits.max_memory}MB"
            )
            # TODO: Déclencher action de limite (warning, throttling, cleanup)
        
        # Vérification disque
        if limits.max_disk and usage.disk_mb > limits.max_disk:
            logger.warning(
                f"Environment {env.id} exceeded disk limit: "
                f"{usage.disk_mb:.1f}MB > {limits.max_disk}MB"
            )
        
        # Vérification nombre de processus
        if usage.active_processes > limits.max_processes:
            logger.warning(
                f"Environment {env.id} exceeded process limit: "
                f"{usage.active_processes} > {limits.max_processes}"
            )
    
    async def _cleanup_old_history(self):
        """Nettoyage de l'historique ancien"""
        current_time = time.time()
        
        for env_id, history in list(self.resource_history.items()):
            # Suppression des mesures de plus de 5 minutes
            cutoff_time = current_time - 300
            
            filtered_history = [
                usage for usage in history
                if usage.timestamp.timestamp() > cutoff_time
            ]
            
            if filtered_history:
                self.resource_history[env_id] = filtered_history
            else:
                # Environnement probablement terminé
                del self.resource_history[env_id]


class PerformanceMonitor:
    """Monitoring des performances système globales"""
    
    def __init__(self):
        self.system_metrics: Dict[str, float] = {}
    
    async def get_system_load(self) -> Dict[str, float]:
        """Récupération de la charge système"""
        try:
            # Charge CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Utilisation mémoire
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / (1024**3)
            
            # Utilisation disque
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            disk_available_gb = disk.free / (1024**3)
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_available_gb": memory_available_gb,
                "disk_percent": disk_percent,
                "disk_available_gb": disk_available_gb,
                "load_average": psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0.0
            }
            
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {}
    
    async def check_system_health(self) -> bool:
        """Vérification de la santé du système"""
        try:
            metrics = await self.get_system_load()
            
            # Critères de santé
            if metrics.get("cpu_percent", 0) > 90:
                logger.warning("High CPU usage detected")
                return False
            
            if metrics.get("memory_percent", 0) > 95:
                logger.warning("High memory usage detected")
                return False
            
            if metrics.get("disk_percent", 0) > 95:
                logger.warning("High disk usage detected")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"System health check failed: {e}")
            return False