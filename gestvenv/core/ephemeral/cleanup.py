"""
Planificateur de nettoyage pour environnements éphémères
"""

import asyncio
import logging
import time
from typing import List, Optional, Dict

from .models import (
    EphemeralEnvironment,
    EphemeralStatus,
    CleanupReason
)
from .exceptions import CleanupException

logger = logging.getLogger(__name__)


class CleanupScheduler:
    """Planificateur automatique de nettoyage"""
    
    def __init__(self, manager):
        self.manager = manager
        self.cleanup_task: Optional[asyncio.Task] = None
        self._shutdown = False
        self.cleanup_history: List[CleanupReason] = []
    
    async def start(self):
        """Démarrage du planificateur"""
        if self.cleanup_task is None:
            logger.info("Starting cleanup scheduler")
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop(self):
        """Arrêt du planificateur"""
        self._shutdown = True
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self.cleanup_task = None
        logger.info("Cleanup scheduler stopped")
    
    async def cleanup_inactive(self):
        """Nettoyage des environnements inactifs"""
        environments = await self.manager.list_environments()
        cleaned_count = 0
        
        for env in environments:
            if await self._should_cleanup_inactive(env):
                try:
                    await self.manager._cleanup_environment(env)
                    cleaned_count += 1
                    
                    reason = CleanupReason(
                        reason="inactive_timeout",
                        triggered_by="cleanup_scheduler"
                    )
                    self.cleanup_history.append(reason)
                    
                    logger.info(f"Cleaned up inactive environment: {env.id}")
                    
                except Exception as e:
                    logger.error(f"Failed to cleanup inactive environment {env.id}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} inactive environments")
        
        return cleaned_count
    
    async def cleanup_expired(self):
        """Nettoyage des environnements expirés"""
        environments = await self.manager.list_environments()
        cleaned_count = 0
        
        for env in environments:
            if env.is_expired():
                try:
                    await self.manager._cleanup_environment(env)
                    cleaned_count += 1
                    
                    reason = CleanupReason(
                        reason="ttl_expired",
                        triggered_by="cleanup_scheduler"
                    )
                    self.cleanup_history.append(reason)
                    
                    logger.info(f"Cleaned up expired environment: {env.id} (age: {env.age_seconds}s)")
                    
                except Exception as e:
                    logger.error(f"Failed to cleanup expired environment {env.id}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired environments")
        
        return cleaned_count
    
    async def cleanup_failed(self):
        """Nettoyage des environnements en échec"""
        environments = await self.manager.list_environments()
        cleaned_count = 0
        
        for env in environments:
            if env.status == EphemeralStatus.FAILED:
                try:
                    await self.manager._cleanup_environment(env, force=True)
                    cleaned_count += 1
                    
                    reason = CleanupReason(
                        reason="failed_state",
                        triggered_by="cleanup_scheduler",
                        forced=True
                    )
                    self.cleanup_history.append(reason)
                    
                    logger.info(f"Cleaned up failed environment: {env.id}")
                    
                except Exception as e:
                    logger.error(f"Failed to cleanup failed environment {env.id}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} failed environments")
        
        return cleaned_count
    
    async def emergency_cleanup_all(self):
        """Nettoyage d'urgence de tous les environnements"""
        logger.warning("Starting emergency cleanup of all environments")
        
        environments = await self.manager.list_environments()
        
        # Nettoyage en parallèle pour plus de rapidité
        cleanup_tasks = []
        for env in environments:
            task = asyncio.create_task(self._emergency_cleanup_single(env))
            cleanup_tasks.append(task)
        
        if cleanup_tasks:
            results = await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
            success_count = sum(1 for r in results if r is True)
            error_count = len(results) - success_count
            
            logger.warning(
                f"Emergency cleanup completed: {success_count} success, {error_count} errors"
            )
    
    async def force_cleanup_old(self):
        """Nettoyage forcé des environnements anciens"""
        environments = await self.manager.list_environments()
        cleaned_count = 0
        
        force_cleanup_age = self.manager.config.force_cleanup_after
        
        for env in environments:
            if env.age_seconds > force_cleanup_age:
                try:
                    await self.manager._cleanup_environment(env, force=True)
                    cleaned_count += 1
                    
                    reason = CleanupReason(
                        reason="force_cleanup_old",
                        triggered_by="cleanup_scheduler",
                        forced=True
                    )
                    self.cleanup_history.append(reason)
                    
                    logger.warning(
                        f"Force cleaned up old environment: {env.id} (age: {env.age_seconds}s)"
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to force cleanup old environment {env.id}: {e}")
        
        if cleaned_count > 0:
            logger.warning(f"Force cleaned up {cleaned_count} old environments")
        
        return cleaned_count
    
    async def _cleanup_loop(self):
        """Boucle principale de nettoyage"""
        cycle_count = 0
        
        while not self._shutdown:
            try:
                cycle_count += 1
                logger.debug(f"Cleanup cycle {cycle_count}")
                
                # Nettoyage des environnements expirés
                await self.cleanup_expired()
                
                # Nettoyage des environnements inactifs
                await self.cleanup_inactive()
                
                # Nettoyage des environnements en échec
                await self.cleanup_failed()
                
                # Nettoyage forcé périodique (toutes les 10 minutes)
                if cycle_count % 10 == 0:
                    await self.force_cleanup_old()
                
                # Nettoyage de l'historique de cleanup
                if cycle_count % 60 == 0:  # Toutes les heures
                    await self._cleanup_history()
                
                # Attente avant le prochain cycle
                await asyncio.sleep(self.manager.config.cleanup_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(60)  # Attente plus longue en cas d'erreur
    
    async def _should_cleanup_inactive(self, env: EphemeralEnvironment) -> bool:
        """Détermine si un environnement doit être nettoyé pour inactivité"""
        if not env.auto_cleanup:
            return False
        
        if not env.is_active:
            return False
        
        return env.is_idle_expired()
    
    async def _emergency_cleanup_single(self, env: EphemeralEnvironment) -> bool:
        """Nettoyage d'urgence d'un seul environnement"""
        try:
            await self.manager._cleanup_environment(env, force=True)
            
            reason = CleanupReason(
                reason="emergency_shutdown",
                triggered_by="cleanup_scheduler",
                forced=True
            )
            self.cleanup_history.append(reason)
            
            return True
            
        except Exception as e:
            logger.error(f"Emergency cleanup failed for {env.id}: {e}")
            return False
    
    async def _cleanup_history(self):
        """Nettoyage de l'historique de cleanup"""
        # Conservation des 100 derniers nettoyages seulement
        if len(self.cleanup_history) > 100:
            self.cleanup_history = self.cleanup_history[-100:]
            logger.debug("Cleaned up cleanup history")
    
    async def get_cleanup_stats(self) -> Dict[str, int]:
        """Statistiques de nettoyage"""
        total_cleanups = len(self.cleanup_history)
        
        # Comptage par raison
        reason_counts = {}
        forced_count = 0
        
        for cleanup in self.cleanup_history:
            reason = cleanup.reason
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
            
            if cleanup.forced:
                forced_count += 1
        
        return {
            "total_cleanups": total_cleanups,
            "forced_cleanups": forced_count,
            "by_reason": reason_counts
        }


class OrphanedResourceCleaner:
    """Nettoyeur de ressources orphelines"""
    
    def __init__(self, storage_manager):
        self.storage_manager = storage_manager
    
    async def cleanup_orphaned_storage(self) -> int:
        """Nettoyage du stockage orphelin"""
        try:
            await self.storage_manager.cleanup_orphaned()
            logger.info("Orphaned storage cleanup completed")
            return 1
        except Exception as e:
            logger.error(f"Orphaned storage cleanup failed: {e}")
            return 0
    
    async def cleanup_orphaned_processes(self) -> int:
        """Nettoyage des processus orphelins"""
        # TODO: Implémentation du nettoyage des processus orphelins
        # Recherche de processus Python/uv/pip isolés sans environnement parent
        cleaned_count = 0
        
        try:
            import psutil
            
            # Recherche de processus suspects
            suspect_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cwd']):
                try:
                    info = proc.info
                    
                    # Recherche de processus liés à gestvenv éphémère
                    if info['cmdline'] and any(
                        'gestvenv-ephemeral' in arg for arg in info['cmdline']
                    ):
                        # Vérification si le répertoire de travail existe encore
                        if info['cwd'] and 'gestvenv-ephemeral' in info['cwd']:
                            if not Path(info['cwd']).exists():
                                suspect_processes.append(proc)
                
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            # Nettoyage des processus orphelins
            for proc in suspect_processes:
                try:
                    logger.warning(f"Terminating orphaned process: {proc.pid}")
                    proc.terminate()
                    
                    # Attente de terminaison gracieuse
                    try:
                        proc.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        proc.kill()
                    
                    cleaned_count += 1
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} orphaned processes")
            
        except Exception as e:
            logger.error(f"Orphaned process cleanup failed: {e}")
        
        return cleaned_count