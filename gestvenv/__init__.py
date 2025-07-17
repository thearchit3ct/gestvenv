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
from gestvenv.core.ephemeral import ephemeral

try:
    from gestvenv.__version__ import __version__
except ImportError:
    __version__ = "unknown"

__all__ = [
    "__version__",
    "EnvironmentManager",
    "BackendManager", 
    "CacheService",
    "DiagnosticService",
    "ephemeral",  # Environments éphémères
    "GestVenvError",
    "EnvironmentNotFoundError",
    "BackendError",
    "CacheError",
    "ValidationError",
]

def get_version() -> str:
    """Retourne la version de GestVenv"""
    return __version__