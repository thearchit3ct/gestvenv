"""
GestVenv - Gestionnaire d'environnements virtuels Python moderne
"""

from gestvenv.core.environment_manager import EnvironmentManager
from gestvenv.core.exceptions import (
    GestVenvError,
    EnvironmentNotFoundError,
    BackendError,
    CacheError,
    ValidationError,
)
from gestvenv.backends.backend_manager import BackendManager
from gestvenv.services.cache_service import CacheService
from gestvenv.services.diagnostic_service import DiagnosticService
from gestvenv.ephemeral import ephemeral, ephemeral_sync

try:
    # D'abord essayer la version statique
    from gestvenv._version import __version__
except ImportError:
    try:
        # Sinon utiliser la version générée par setuptools_scm
        from gestvenv.__version__ import __version__
    except ImportError:
        __version__ = "2.0.0"

__all__ = [
    "__version__",
    "EnvironmentManager",
    "BackendManager", 
    "CacheService",
    "DiagnosticService",
    "ephemeral",  # Environments éphémères
    "ephemeral_sync",  # Version synchrone
    "GestVenvError",
    "EnvironmentNotFoundError",
    "BackendError",
    "CacheError",
    "ValidationError",
]

def get_version() -> str:
    """Retourne la version de GestVenv"""
    return __version__