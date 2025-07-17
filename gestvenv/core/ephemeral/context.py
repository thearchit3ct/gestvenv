"""
Context manager pour environnements éphémères
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional, AsyncIterator

from .manager import EphemeralManager
from .models import EphemeralEnvironment, EphemeralConfig

logger = logging.getLogger(__name__)

# Instance globale du gestionnaire
_global_manager: Optional[EphemeralManager] = None


async def get_manager() -> EphemeralManager:
    """Récupération du gestionnaire global"""
    global _global_manager
    
    if _global_manager is None:
        config = EphemeralConfig()
        _global_manager = EphemeralManager(config)
        await _global_manager.start()
        
        # Enregistrement du cleanup à la fermeture
        import atexit
        atexit.register(lambda: asyncio.create_task(_cleanup_manager()))
    
    return _global_manager


async def _cleanup_manager():
    """Nettoyage du gestionnaire global"""
    global _global_manager
    
    if _global_manager:
        await _global_manager.stop()
        _global_manager = None


@asynccontextmanager
async def ephemeral(
    name: Optional[str] = None,
    **kwargs
) -> AsyncIterator[EphemeralEnvironment]:
    """
    Context manager pour création d'environnement éphémère
    
    Usage:
        async with ephemeral("test-env") as env:
            # Utilisation de l'environnement
            await env.execute("pip install requests")
            result = await env.execute("python -c 'import requests; print(requests.__version__)'")
            print(result.stdout)
    
    Args:
        name: Nom optionnel de l'environnement
        **kwargs: Arguments de configuration supplémentaires
    
    Returns:
        EphemeralEnvironment: Environnement éphémère configuré et prêt
    """
    manager = await get_manager()
    
    async with manager.create_ephemeral(name, **kwargs) as env:
        # Ajout de méthodes de convenance à l'environnement
        env.execute = lambda cmd, **exec_kwargs: manager.lifecycle_controller.execute_command(
            env, cmd, **exec_kwargs
        )
        env.install = lambda packages, **install_kwargs: manager.lifecycle_controller.install_packages(
            env, packages if isinstance(packages, list) else [packages], **install_kwargs
        )
        
        yield env


# Alias pour compatibilité
create_ephemeral = ephemeral


# Version synchrone pour les cas simples (wrapper autour de la version async)
def ephemeral_sync(name: Optional[str] = None, **kwargs):
    """
    Version synchrone du context manager éphémère
    
    Note: Utilise asyncio.run() en interne, donc ne peut pas être utilisé
    dans un contexte async existant.
    """
    import asyncio
    
    class SyncEphemeralContext:
        def __init__(self, name, kwargs):
            self.name = name
            self.kwargs = kwargs
            self.env = None
            self.manager = None
        
        def __enter__(self):
            # Création d'une nouvelle boucle d'événements
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Création de l'environnement
                self.env = loop.run_until_complete(self._create_env())
                return self.env
            except Exception:
                loop.close()
                raise
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            loop = asyncio.get_event_loop()
            try:
                # Nettoyage de l'environnement
                loop.run_until_complete(self._cleanup_env())
            finally:
                loop.close()
        
        async def _create_env(self):
            self.manager = await get_manager()
            # Note: Dans la version sync, on ne peut pas utiliser le context manager async
            # Donc on crée et nettoie manuellement
            env = await self.manager._create_environment(self.name, **self.kwargs)
            await self.manager._register_environment(env)
            
            # Ajout des méthodes de convenance
            env.execute = lambda cmd, **exec_kwargs: asyncio.get_event_loop().run_until_complete(
                self.manager.lifecycle_controller.execute_command(env, cmd, **exec_kwargs)
            )
            env.install = lambda packages, **install_kwargs: asyncio.get_event_loop().run_until_complete(
                self.manager.lifecycle_controller.install_packages(
                    env, packages if isinstance(packages, list) else [packages], **install_kwargs
                )
            )
            
            return env
        
        async def _cleanup_env(self):
            if self.env and self.manager:
                await self.manager._cleanup_environment(self.env)
    
    return SyncEphemeralContext(name, kwargs)


# Fonctions utilitaires
async def list_active_environments():
    """Liste tous les environnements éphémères actifs"""
    manager = await get_manager()
    return await manager.list_environments()


async def cleanup_environment(env_id: str, force: bool = False):
    """Nettoyage manuel d'un environnement par son ID"""
    manager = await get_manager()
    return await manager.cleanup_environment(env_id, force=force)


async def get_resource_usage():
    """Récupération de l'usage global des ressources"""
    manager = await get_manager()
    return await manager.get_resource_usage()


async def shutdown_manager():
    """Arrêt manuel du gestionnaire global"""
    await _cleanup_manager()