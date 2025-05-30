"""
GestVenv - Gestionnaire d'Environnements Virtuels Python.

GestVenv est un outil qui simplifie et centralise la gestion des environnements virtuels Python,
offrant une alternative unifiée aux outils existants comme venv, virtualenv et pipenv.

Ce package fournit une API complète pour :
- Créer, supprimer et gérer des environnements virtuels
- Installer et gérer des packages Python
- Gérer un cache local pour le mode hors ligne
- Diagnostiquer et réparer les environnements
- Exporter et importer des configurations
- Surveiller et optimiser les performances

Usage de base:
    >>> import gestvenv
    >>> manager = gestvenv.EnvironmentManager()
    >>> success, message = manager.create_environment("mon_projet", packages="flask,requests")
    >>> print(f"Création: {message}")

Usage avec raccourcis:
    >>> import gestvenv
    >>> # Créer un environnement rapidement
    >>> env = gestvenv.create_environment("mon_projet")
    >>> # Lister tous les environnements
    >>> envs = gestvenv.list_environments()
"""

# Informations sur le package
__version__ = "1.1.1"
__author__ = "thearchit3ct"
__email__ = "thearchit3ct@outlook.fr"
__license__ = "MIT"
__description__ = "Gestionnaire d'environnements virtuels Python avancé"
__url__ = "https://github.com/thearchit3ct/gestvenv"

# Configuration du logging par défaut
import logging
import sys
from typing import Optional, List, Dict, Any, Tuple, Union

# Empêcher la propagation des logs vers le logger racine par défaut
logging.getLogger(__name__).addHandler(logging.NullHandler())

# Imports principaux pour l'API publique
try:
    # Core components
    from .core.env_manager import EnvironmentManager
    from .core.config_manager import ConfigManager
    from .core.models import EnvironmentInfo, PackageInfo, ConfigInfo, EnvironmentHealth
    
    # Services principaux
    from .services.environment_service import EnvironmentService
    from .services.package_service import PackageService
    from .services.system_service import SystemService
    from .services.cache_service import CacheService
    from .services.diagnostic_services import DiagnosticService
    
    # Utilitaires les plus couramment utilisés
    from .utils.logging_utils import setup_logging, get_logger, LogCategory
    from .utils.path_utils import get_default_data_dir, resolve_path
    from .utils.validation_utils import is_valid_name, is_valid_path
    
    _IMPORTS_SUCCESSFUL = True
    
except ImportError as e:
    # En cas d'erreur d'import, on continue mais on marque l'erreur
    _IMPORTS_SUCCESSFUL = False
    _IMPORT_ERROR = str(e)
    
    # Définir des classes de substitution pour éviter les erreurs
    class _ImportError:
        def __init__(self, *args, **kwargs):
            raise ImportError(f"GestVenv import failed: {_IMPORT_ERROR}")
    
    EnvironmentManager = _ImportError
    ConfigManager = _ImportError

# Instance globale du gestionnaire principal (lazy loading)
_global_manager: Optional[EnvironmentManager] = None

def get_version() -> str:
    """
    Retourne la version actuelle de GestVenv.
    
    Returns:
        str: Version du package
    """
    return __version__

def get_info() -> Dict[str, str]:
    """
    Retourne les informations complètes sur le package.
    
    Returns:
        Dict[str, str]: Informations sur le package
    """
    return {
        "name": "gestvenv",
        "version": __version__,
        "author": __author__,
        "email": __email__,
        "license": __license__,
        "description": __description__,
        "url": __url__
    }

def _get_global_manager() -> EnvironmentManager:
    """
    Obtient l'instance globale du gestionnaire d'environnements.
    
    Returns:
        EnvironmentManager: Instance globale
    """
    global _global_manager
    
    if not _IMPORTS_SUCCESSFUL:
        raise ImportError(f"GestVenv imports failed: {_IMPORT_ERROR}")
    
    if _global_manager is None:
        _global_manager = EnvironmentManager()
    
    return _global_manager

def setup_gestvenv_logging(debug: bool = False, structured: bool = False, 
                          quiet: bool = False, logs_dir: Optional[str] = None) -> None:
    """
    Configure le système de logging pour GestVenv.
    
    Args:
        debug: Si True, active le niveau DEBUG
        structured: Si True, utilise le format JSON
        quiet: Si True, réduit la verbosité console
        logs_dir: Répertoire des logs personnalisé
    """
    if not _IMPORTS_SUCCESSFUL:
        raise ImportError(f"GestVenv imports failed: {_IMPORT_ERROR}")
    
    from pathlib import Path
    logs_path = Path(logs_dir) if logs_dir else None
    setup_logging(debug, structured, quiet, logs_path)

# =====================================================================
# API DE RACCOURCIS POUR LES OPÉRATIONS COURANTES
# =====================================================================

def create_environment(name: str, python_version: Optional[str] = None,
                      packages: Optional[str] = None, path: Optional[str] = None,
                      offline: bool = False, requirements_file: Optional[str] = None,
                      description: Optional[str] = None) -> Tuple[bool, str]:
    """
    Raccourci pour créer un environnement virtuel.
    
    Args:
        name: Nom de l'environnement
        python_version: Version Python à utiliser
        packages: Liste de packages à installer (séparés par des virgules)
        path: Chemin personnalisé pour l'environnement
        offline: Si True, utilise uniquement le cache local
        requirements_file: Chemin vers un fichier requirements.txt
        description: Description de l'environnement
        
    Returns:
        Tuple[bool, str]: (succès, message)
    
    Example:
        >>> success, msg = gestvenv.create_environment("mon_projet", packages="flask,requests")
        >>> print(f"Création: {msg}")
    """
    manager = _get_global_manager()
    
    metadata = {}
    if description:
        metadata["description"] = description
    
    return manager.create_environment(
        name=name,
        python_version=python_version,
        packages=packages,
        path=path,
        offline=offline,
        requirements_file=requirements_file,
        metadata=metadata
    )

def delete_environment(name: str, force: bool = False) -> Tuple[bool, str]:
    """
    Raccourci pour supprimer un environnement virtuel.
    
    Args:
        name: Nom de l'environnement à supprimer
        force: Si True, force la suppression sans vérifications
        
    Returns:
        Tuple[bool, str]: (succès, message)
    """
    manager = _get_global_manager()
    return manager.delete_environment(name, force)

def list_environments() -> List[Dict[str, Any]]:
    """
    Raccourci pour lister tous les environnements.
    
    Returns:
        List[Dict[str, Any]]: Liste des environnements avec leurs détails
    
    Example:
        >>> envs = gestvenv.list_environments()
        >>> for env in envs:
        ...     print(f"{env['name']}: {env['python_version']}")
    """
    manager = _get_global_manager()
    return manager.list_environments()

def activate_environment(name: str) -> Tuple[bool, str]:
    """
    Raccourci pour activer un environnement.
    
    Args:
        name: Nom de l'environnement à activer
        
    Returns:
        Tuple[bool, str]: (succès, commande d'activation)
    """
    manager = _get_global_manager()
    return manager.activate_environment(name)

def get_active_environment() -> Optional[str]:
    """
    Raccourci pour obtenir le nom de l'environnement actif.
    
    Returns:
        Optional[str]: Nom de l'environnement actif ou None
    """
    manager = _get_global_manager()
    return manager.get_active_environment()

def install_packages(env_name: str, packages: str, requirements_file: Optional[str] = None,
                    offline: bool = False) -> Tuple[bool, str]:
    """
    Raccourci pour installer des packages dans un environnement.
    
    Args:
        env_name: Nom de l'environnement
        packages: Packages à installer (séparés par des virgules)
        requirements_file: Chemin vers un fichier requirements.txt
        offline: Force le mode hors ligne
        
    Returns:
        Tuple[bool, str]: (succès, message)
    """
    manager = _get_global_manager()
    return manager.install_packages(
        env_name=env_name,
        packages=packages,
        requirements_file=requirements_file,
        offline=offline
    )

def export_environment(name: str, output_path: Optional[str] = None,
                      format_type: str = "json") -> Tuple[bool, str]:
    """
    Raccourci pour exporter un environnement.
    
    Args:
        name: Nom de l'environnement à exporter
        output_path: Chemin de sortie
        format_type: Format d'export ('json' ou 'requirements')
        
    Returns:
        Tuple[bool, str]: (succès, message ou chemin du fichier)
    """
    manager = _get_global_manager()
    return manager.export_environment(name, output_path, format_type)

def get_environment_info(name: str) -> Optional[Dict[str, Any]]:
    """
    Raccourci pour obtenir des informations détaillées sur un environnement.
    
    Args:
        name: Nom de l'environnement
        
    Returns:
        Optional[Dict[str, Any]]: Informations sur l'environnement ou None
    """
    manager = _get_global_manager()
    return manager.get_environment_info(name)

def diagnose_environment(name: str, full_check: bool = False) -> Tuple[bool, Dict[str, Any]]:
    """
    Raccourci pour diagnostiquer un environnement.
    
    Args:
        name: Nom de l'environnement à diagnostiquer
        full_check: Si True, effectue un diagnostic complet
        
    Returns:
        Tuple[bool, Dict[str, Any]]: (santé globale, rapport de diagnostic)
    """
    manager = _get_global_manager()
    return manager.diagnose_environment(name, full_check)

def get_system_info() -> Dict[str, Any]:
    """
    Raccourci pour obtenir des informations système.
    
    Returns:
        Dict[str, Any]: Informations détaillées sur le système
    """
    manager = _get_global_manager()
    return manager.get_system_info()

# =====================================================================
# FONCTIONS UTILITAIRES PUBLIQUES
# =====================================================================

def check_requirements() -> Dict[str, Any]:
    """
    Vérifie que tous les prérequis pour GestVenv sont installés.
    
    Returns:
        Dict[str, Any]: Rapport de vérification des prérequis
    """
    if not _IMPORTS_SUCCESSFUL:
        return {
            "status": "error",
            "message": f"Import failed: {_IMPORT_ERROR}",
            "requirements_met": False
        }
    
    try:
        system_service = SystemService()
        
        report = {
            "status": "checking",
            "requirements_met": True,
            "python_version": None,
            "pip_available": False,
            "venv_available": False,
            "system_info": {},
            "issues": [],
            "recommendations": []
        }
        
        # Vérifier Python
        python_info = system_service.get_python_info()
        report["python_version"] = python_info["version"]
        report["system_info"] = system_service.get_system_info()
        
        # Vérifier pip
        report["pip_available"] = system_service.check_command_exists("pip")
        if not report["pip_available"]:
            report["issues"].append("pip n'est pas disponible")
            report["recommendations"].append("Installer pip")
            report["requirements_met"] = False
        
        # Vérifier venv
        import subprocess
        try:
            result = subprocess.run(["python", "-m", "venv", "--help"], 
                                  capture_output=True, timeout=5)
            report["venv_available"] = result.returncode == 0
        except Exception:
            report["venv_available"] = False
        
        if not report["venv_available"]:
            report["issues"].append("Le module venv n'est pas disponible")
            report["recommendations"].append("Mettre à jour Python ou installer virtualenv")
            report["requirements_met"] = False
        
        # Déterminer le statut final
        if report["requirements_met"]:
            report["status"] = "ok"
        else:
            report["status"] = "missing_requirements"
        
        return report
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error checking requirements: {str(e)}",
            "requirements_met": False
        }

def validate_environment_name(name: str) -> Tuple[bool, str]:
    """
    Valide un nom d'environnement.
    
    Args:
        name: Nom à valider
        
    Returns:
        Tuple[bool, str]: (validité, message d'erreur si invalide)
    """
    if not _IMPORTS_SUCCESSFUL:
        raise ImportError(f"GestVenv imports failed: {_IMPORT_ERROR}")
    
    return is_valid_name(name)

def get_default_environments_directory() -> str:
    """
    Retourne le répertoire par défaut des environnements.
    
    Returns:
        str: Chemin vers le répertoire par défaut
    """
    if not _IMPORTS_SUCCESSFUL:
        raise ImportError(f"GestVenv imports failed: {_IMPORT_ERROR}")
    
    return str(get_default_data_dir() / "environments")

# =====================================================================
# GESTION DES ERREURS ET STATUT
# =====================================================================

def is_available() -> bool:
    """
    Vérifie si GestVenv est correctement importé et disponible.
    
    Returns:
        bool: True si GestVenv est disponible
    """
    return _IMPORTS_SUCCESSFUL

def get_import_error() -> Optional[str]:
    """
    Retourne l'erreur d'import si elle existe.
    
    Returns:
        Optional[str]: Message d'erreur d'import ou None
    """
    return _IMPORT_ERROR if not _IMPORTS_SUCCESSFUL else None

# =====================================================================
# API PUBLIQUE - EXPORTS
# =====================================================================

__all__ = [
    # Informations sur le package
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    "get_version",
    "get_info",
    
    # Classes principales (si imports réussis)
    "EnvironmentManager",
    "ConfigManager",
    "EnvironmentInfo",
    "PackageInfo",
    "ConfigInfo",
    "EnvironmentHealth",
    
    # Services
    "EnvironmentService",
    "PackageService",
    "SystemService", 
    "CacheService",
    "DiagnosticService",
    
    # Configuration
    "setup_gestvenv_logging",
    
    # API de raccourcis
    "create_environment",
    "delete_environment",
    "list_environments",
    "activate_environment",
    "get_active_environment",
    "install_packages",
    "export_environment",
    "get_environment_info",
    "diagnose_environment",
    "get_system_info",
    
    # Utilitaires
    "check_requirements",
    "validate_environment_name",
    "get_default_environments_directory",
    "is_available",
    "get_import_error",
    
    # Constantes utiles
    "LogCategory",
]

# Ajouter les classes seulement si les imports ont réussi
if not _IMPORTS_SUCCESSFUL:
    # Retirer les classes des exports si import échoué
    __all__ = [item for item in __all__ if item not in [
        "EnvironmentManager", "ConfigManager", "EnvironmentInfo", 
        "PackageInfo", "ConfigInfo", "EnvironmentHealth",
        "EnvironmentService", "PackageService", "SystemService", 
        "CacheService", "DiagnosticService", "LogCategory"
    ]]

# Message de bienvenue optionnel (seulement en mode debug)
if __debug__ and _IMPORTS_SUCCESSFUL:
    import os
    if os.environ.get("GESTVENV_VERBOSE"):
        print(f"GestVenv {__version__} initialized successfully")
        print(f"Default environments directory: {get_default_environments_directory()}")