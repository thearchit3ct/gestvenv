"""
Système d'environnements éphémères GestVenv
Environnements temporaires avec nettoyage automatique
"""

from .models import (
    EphemeralEnvironment,
    EphemeralConfig,
    EphemeralStatus,
    IsolationLevel,
    StorageBackend,
    SecurityMode
)
from .manager import EphemeralManager
from .exceptions import (
    EphemeralException,
    ResourceExhaustedException,
    EnvironmentCreationException,
    CleanupException
)
from .context import (
    ephemeral,
    ephemeral_sync,
    create_ephemeral,
    list_active_environments,
    cleanup_environment,
    get_resource_usage,
    shutdown_manager
)

__all__ = [
    # Context managers (API principal)
    'ephemeral',
    'ephemeral_sync', 
    'create_ephemeral',
    
    # Fonctions utilitaires
    'list_active_environments',
    'cleanup_environment',
    'get_resource_usage',
    'shutdown_manager',
    
    # Models
    'EphemeralEnvironment',
    'EphemeralConfig', 
    'EphemeralStatus',
    'IsolationLevel',
    'StorageBackend',
    'SecurityMode',
    
    # Manager
    'EphemeralManager',
    
    # Exceptions
    'EphemeralException',
    'ResourceExhaustedException',
    'EnvironmentCreationException',
    'CleanupException'
]