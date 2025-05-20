# Package initialization
"""
Module core de GestVenv.

Ce package contient les composants principaux de GestVenv:
- models: Classes de données et structures partagées
- config_manager: Gestion des configurations
- env_manager: Gestion des environnements virtuels
"""

# Exports principaux pour faciliter l'importation
from .models import EnvironmentInfo, PackageInfo, ConfigInfo
from .env_manager import EnvironmentManager
from .config_manager import ConfigManager

__all__ = [
    'EnvironmentInfo', 
    'PackageInfo', 
    'ConfigInfo',
    'EnvironmentManager',
    'ConfigManager'
]