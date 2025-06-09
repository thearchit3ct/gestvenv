"""
Module core de GestVenv - Gestionnaire d'Environnements Virtuels Python v1.1.

Ce package contient les composants principaux et les abstractions de base de GestVenv.
Il fournit une interface unifiée pour la gestion des environnements virtuels Python,
des packages et de leur configuration.

Nouveautés v1.1:
    - Support pyproject.toml (PEP 621)
    - Backends modulaires (pip, uv, poetry, pdm)
    - Migration automatique v1.0 → v1.1
    - Templates de projets
    - Diagnostic avancé

Composants principaux:
    - models: Classes de données et structures partagées (étendu v1.1)
    - env_manager: Gestionnaire principal des environnements virtuels
    - config_manager: Gestionnaire de configuration et persistance (nouveau v1.1)
    - strategies: Stratégies de gestion (nouveau v1.1)

Classes de données:
    - EnvironmentInfo: Représente un environnement virtuel avec ses métadonnées (étendu)
    - PackageInfo: Représente un package Python avec ses dépendances (étendu)
    - PyProjectInfo: Métadonnées pyproject.toml (nouveau v1.1)
    - EnvironmentHealth: État de santé d'un environnement virtuel
    - ConfigInfo: Configuration globale de GestVenv

Usage:
    from gestvenv.core import EnvironmentManager, ConfigManager
    from gestvenv.core import EnvironmentInfo, PyProjectInfo
    
    # Créer un gestionnaire d'environnements
    manager = EnvironmentManager()
    
    # Créer un environnement avec pyproject.toml
    success, message = manager.create_environment(
        name="mon_projet",
        python_version="python3.11",
        from_pyproject="./pyproject.toml"
    )
"""

import logging
from typing import Optional

# Configuration du logger pour le module core
logger = logging.getLogger(__name__)

# Imports des classes de données (models) - avec gestion d'erreurs
try:
    from .models import (
        # Classes existantes v1.0 (étendues)
        EnvironmentInfo,
        PackageInfo, 
        EnvironmentHealth,
        ConfigInfo,
        
        # Nouvelles classes v1.1
        PyProjectInfo,
        BackendType,
        SourceFileType,
        HealthStatus,
        
        # Constantes et utilitaires
        SCHEMA_VERSION,
        COMPATIBLE_VERSIONS,
    )
    _MODELS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Erreur import models: {e}")
    _MODELS_AVAILABLE = False

# Imports des gestionnaires principaux
try:
    from .env_manager import EnvironmentManager
    _ENV_MANAGER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Erreur import EnvironmentManager: {e}")
    EnvironmentManager = None
    _ENV_MANAGER_AVAILABLE = False

try:
    from .config_manager import ConfigManager
    _CONFIG_MANAGER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Erreur import ConfigManager: {e}")
    ConfigManager = None
    _CONFIG_MANAGER_AVAILABLE = False

# Imports des nouveaux modules v1.1
try:
    from .strategies import (
        GestVenvStrategies,
        get_default_strategies,
        BackendSelectionStrategy,
        CacheStrategy,
    )
    _STRATEGIES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Stratégies non disponibles: {e}")
    _STRATEGIES_AVAILABLE = False

try:
    from .exceptions import (
        GestVenvError,
        EnvironmentError,
        ConfigurationError,
        BackendError,
        MigrationError,
        ValidationError,
    )
    _EXCEPTIONS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Exceptions personnalisées non disponibles: {e}")
    _EXCEPTIONS_AVAILABLE = False

# Information sur le module
__version__ = "1.1.1"
__author__ = "thearchit3ct"

# Exports publics du module core
__all__ = [
    # Gestionnaires principaux
    'EnvironmentManager',
    'ConfigManager',
    
    # Métadonnées
    '__version__',
    '__author__'
]

# Ajouter les classes de données si disponibles
if _MODELS_AVAILABLE:
    __all__.extend([
        # Classes de données v1.0 (étendues)
        'EnvironmentInfo',
        'PackageInfo', 
        'EnvironmentHealth',
        'ConfigInfo',
        
        # Nouvelles classes v1.1
        'PyProjectInfo',
        'BackendType',
        'SourceFileType',
        'HealthStatus',
        
        # Constantes
        'SCHEMA_VERSION',
        'COMPATIBLE_VERSIONS',
    ])

# Ajouter les stratégies si disponibles
if _STRATEGIES_AVAILABLE:
    __all__.extend([
        'GestVenvStrategies',
        'get_default_strategies',
        'BackendSelectionStrategy',
        'CacheStrategy',
    ])

# Ajouter les exceptions si disponibles
if _EXCEPTIONS_AVAILABLE:
    __all__.extend([
        'GestVenvError',
        'EnvironmentError',
        'ConfigurationError',
        'BackendError',
        'MigrationError',
        'ValidationError',
    ])

def get_core_status() -> dict:
    """
    Retourne le statut des composants du module core.
    
    Returns:
        dict: Statut de chaque composant
    """
    return {
        'models': _MODELS_AVAILABLE,
        'env_manager': _ENV_MANAGER_AVAILABLE,
        'config_manager': _CONFIG_MANAGER_AVAILABLE,
        'strategies': _STRATEGIES_AVAILABLE,
        'exceptions': _EXCEPTIONS_AVAILABLE,
    }

# Validation des imports au niveau du module
def _validate_imports() -> None:
    """Valide que tous les imports critiques sont disponibles."""
    if not _ENV_MANAGER_AVAILABLE or not _CONFIG_MANAGER_AVAILABLE:
        logger.error("Composants critiques du core non disponibles")
        if __debug__:
            print(f"Statut core: {get_core_status()}")

# Validation à l'import
_validate_imports()