"""
Module core de GestVenv - Gestionnaire d'Environnements Virtuels Python.

Ce package contient les composants principaux et les abstractions de base de GestVenv.
Il fournit une interface unifiée pour la gestion des environnements virtuels Python,
des packages et de leur configuration.

Composants principaux:
    - models: Classes de données et structures partagées
    - env_manager: Gestionnaire principal des environnements virtuels
    - config_manager: Gestionnaire de configuration et persistance

Classes de données:
    - EnvironmentInfo: Représente un environnement virtuel avec ses métadonnées
    - PackageInfo: Représente un package Python avec ses dépendances
    - EnvironmentHealth: État de santé d'un environnement virtuel
    - ConfigInfo: Configuration globale de GestVenv

Gestionnaires:
    - EnvironmentManager: Interface principale pour toutes les opérations sur les environnements
    - ConfigManager: Gestion de la configuration, sauvegarde et restauration

Usage:
    from gestvenv.core import EnvironmentManager, ConfigManager
    from gestvenv.core import EnvironmentInfo, PackageInfo
    
    # Créer un gestionnaire d'environnements
    manager = EnvironmentManager()
    
    # Créer un nouvel environnement
    success, message = manager.create_environment(
        name="mon_projet",
        python_version="python3.11",
        packages="flask,requests"
    )
"""

# Imports des classes de données (models)
from .models import (
    EnvironmentInfo,
    PackageInfo, 
    EnvironmentHealth,
    ConfigInfo
)

# Imports des gestionnaires principaux
from .env_manager import EnvironmentManager
from .config_manager import ConfigManager

# Information sur le module
__version__ = "1.1.1"
__author__ = "thearchit3ct"

# Exports publics du module core
__all__ = [
    # Classes de données
    'EnvironmentInfo',
    'PackageInfo', 
    'EnvironmentHealth',
    'ConfigInfo',
    
    # Gestionnaires principaux
    'EnvironmentManager',
    'ConfigManager',
    
    # Métadonnées
    '__version__',
    '__author__'
]

# Validation des imports au niveau du module
def _validate_imports() -> None:
    """Valide que tous les imports critiques sont disponibles."""
    required_modules = {
        'EnvironmentInfo': EnvironmentInfo,
        'PackageInfo': PackageInfo,
        'EnvironmentHealth': EnvironmentHealth,
        'ConfigInfo': ConfigInfo,
        'EnvironmentManager': EnvironmentManager,
        'ConfigManager': ConfigManager,
    }
    
    missing_modules = []
    for name, module in required_modules.items():
        if module is None:
            missing_modules.append(name)
    
    if missing_modules:
        raise ImportError(
            f"Modules critiques manquants dans gestvenv.core: {', '.join(missing_modules)}"
        )

# Valider les imports lors du chargement du module
try:
    _validate_imports()
except ImportError as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Erreur lors de l'initialisation du module core: {e}")
    raise

# Fonction utilitaire pour créer rapidement un gestionnaire d'environnements
def create_manager(config_path=None) -> EnvironmentManager:
    """
    Crée et retourne une instance de EnvironmentManager configurée.
    
    Args:
        config_path (str, optional): Chemin vers le fichier de configuration.
            Si None, utilise le chemin par défaut.
    
    Returns:
        EnvironmentManager: Instance configurée du gestionnaire d'environnements.
    
    Example:
        >>> from gestvenv.core import create_manager
        >>> manager = create_manager()
        >>> environments = manager.list_environments()
    """
    return EnvironmentManager(config_path=config_path)

# Fonction utilitaire pour l'introspection du module
def get_module_info():
    """
    Retourne des informations sur le module core.
    
    Returns:
        dict: Dictionnaire contenant les informations du module.
    """
    return {
        'name': 'gestvenv.core',
        'version': __version__,
        'author': __author__,
        'components': {
            'models': [
                'EnvironmentInfo',
                'PackageInfo', 
                'EnvironmentHealth',
                'ConfigInfo'
            ],
            'managers': [
                'EnvironmentManager',
                'ConfigManager'
            ]
        },
        'description': 'Module principal de GestVenv pour la gestion des environnements virtuels Python'
    }

# Ajout au namespace pour faciliter l'introspection
__all__.extend(['create_manager', 'get_module_info'])

# Documentation des classes principales pour l'aide en ligne
_HELP_TEXT = {
    'EnvironmentManager': """
    Gestionnaire principal pour les environnements virtuels Python.
    
    Fonctionnalités principales:
    - Création et suppression d'environnements
    - Installation et gestion des packages
    - Import/export de configurations
    - Diagnostic et réparation
    """,
    
    'ConfigManager': """
    Gestionnaire de configuration pour GestVenv.
    
    Fonctionnalités principales:
    - Sauvegarde et restauration de configurations
    - Gestion des paramètres globaux
    - Import/export de configurations d'environnements
    - Gestion des sauvegardes automatiques
    """,
    
    'EnvironmentInfo': """
    Classe de données représentant un environnement virtuel.
    
    Contient:
    - Métadonnées de l'environnement (nom, chemin, version Python)
    - Liste des packages installés
    - État de santé de l'environnement
    - Informations de création et de modification
    """,
    
    'PackageInfo': """
    Classe de données représentant un package Python.
    
    Contient:
    - Nom et version du package
    - Dépendances et packages dépendants
    - Métadonnées d'installation
    """
}

def help_component(component_name):
    """
    Affiche l'aide pour un composant spécifique du module core.
    
    Args:
        component_name (str): Nom du composant pour lequel afficher l'aide.
    
    Example:
        >>> from gestvenv.core import help_component
        >>> help_component('EnvironmentManager')
    """
    if component_name in _HELP_TEXT:
        print(f"Aide pour {component_name}:")
        print(_HELP_TEXT[component_name])
    else:
        available_components = list(_HELP_TEXT.keys())
        print(f"Composant '{component_name}' non trouvé.")
        print(f"Composants disponibles: {', '.join(available_components)}")

# Ajout de help_component aux exports
__all__.append('help_component')