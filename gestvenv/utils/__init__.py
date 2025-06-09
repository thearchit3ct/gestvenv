"""
Module utilitaires pour GestVenv v1.1.

Ce package contient tous les utilitaires et helpers utilisés par les autres
modules de GestVenv. Il fournit des fonctions pour la validation, parsing,
migration, gestion des chemins, etc.

Modules utilitaires:
- toml_utils: Parser et utilitaires TOML avec fallback
- pyproject_parser: Parser pyproject.toml PEP 621 complet
- migration_utils: Utilitaires de migration v1.0 → v1.1
- validation_utils: Validateurs pour noms, chemins, versions
- path_utils: Utilitaires de gestion des chemins et fichiers
- format_utils: Formatage et affichage

Usage:
    from gestvenv.utils import TomlHandler, PyProjectParser
    from gestvenv.utils import validate_environment_name
    from gestvenv.utils import ensure_directory, safe_remove_directory
"""

import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

# Configuration du logger pour le module utils
logger = logging.getLogger(__name__)

# Import des parsers et handlers
try:
    from .toml_utils import TomlHandler, TomlError
    _TOML_UTILS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"TomlHandler non disponible: {e}")
    TomlHandler = None
    TomlError = None
    _TOML_UTILS_AVAILABLE = False

try:
    from .pyproject_parser import PyProjectParser, PyProjectError
    _PYPROJECT_PARSER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"PyProjectParser non disponible: {e}")
    PyProjectParser = None
    PyProjectError = None
    _PYPROJECT_PARSER_AVAILABLE = False

# Import des utilitaires de migration
try:
    from .migration_utils import MigrationManager, MigrationError
    _MIGRATION_UTILS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"MigrationManager non disponible: {e}")
    MigrationManager = None
    MigrationError = None
    _MIGRATION_UTILS_AVAILABLE = False

# Import des validateurs
try:
    from .validation_utils import (
        validate_environment_name,
        validate_python_version,
        validate_package_name,
        validate_project_structure,
        ValidationError
    )
    _VALIDATION_UTILS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Utilitaires de validation non disponibles: {e}")
    _VALIDATION_UTILS_AVAILABLE = False

# Import des utilitaires de chemins
try:
    from .path_utils import (
        ensure_directory,
        safe_remove_directory,
        find_project_root,
        resolve_relative_path,
        get_default_data_dir,
        resolve_path
    )
    _PATH_UTILS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Utilitaires de chemins non disponibles: {e}")
    _PATH_UTILS_AVAILABLE = False

# Import des utilitaires de formatage
try:
    from .format_utils import (
        format_size,
        format_duration,
        format_package_list,
        format_table,
        ColorFormatter
    )
    _FORMAT_UTILS_AVAILABLE = True
except ImportError as e:
    logger.info(f"Utilitaires de formatage non disponibles: {e}")
    _FORMAT_UTILS_AVAILABLE = False

# Import des utilitaires de logging
try:
    from .logging_utils import (
        setup_logging,
        get_logger,
        LogCategory,
        configure_verbose_logging
    )
    _LOGGING_UTILS_AVAILABLE = True
except ImportError as e:
    logger.info(f"Utilitaires de logging non disponibles: {e}")
    _LOGGING_UTILS_AVAILABLE = False


# Exports de base
__all__ = []

# Parsers et handlers
if _TOML_UTILS_AVAILABLE:
    __all__.extend(['TomlHandler', 'TomlError'])

if _PYPROJECT_PARSER_AVAILABLE:
    __all__.extend(['PyProjectParser', 'PyProjectError'])

# Migration
if _MIGRATION_UTILS_AVAILABLE:
    __all__.extend(['MigrationManager', 'MigrationError'])

# Validation
if _VALIDATION_UTILS_AVAILABLE:
    __all__.extend([
        'validate_environment_name',
        'validate_python_version', 
        'validate_package_name',
        'validate_project_structure',
        'ValidationError'
    ])

# Chemins
if _PATH_UTILS_AVAILABLE:
    __all__.extend([
        'ensure_directory',
        'safe_remove_directory',
        'find_project_root',
        'resolve_relative_path',
        'get_default_data_dir',
        'resolve_path'
    ])

# Formatage
if _FORMAT_UTILS_AVAILABLE:
    __all__.extend([
        'format_size',
        'format_duration',
        'format_package_list',
        'format_table',
        'ColorFormatter'
    ])

# Logging
if _LOGGING_UTILS_AVAILABLE:
    __all__.extend([
        'setup_logging',
        'get_logger',
        'LogCategory',
        'configure_verbose_logging'
    ])


def get_utils_status() -> Dict[str, bool]:
    """
    Retourne le statut de disponibilité de tous les utilitaires.
    
    Returns:
        Dict[str, bool]: Statut de chaque module utilitaire
    """
    return {
        'toml_utils': _TOML_UTILS_AVAILABLE,
        'pyproject_parser': _PYPROJECT_PARSER_AVAILABLE,
        'migration_utils': _MIGRATION_UTILS_AVAILABLE,
        'validation_utils': _VALIDATION_UTILS_AVAILABLE,
        'path_utils': _PATH_UTILS_AVAILABLE,
        'format_utils': _FORMAT_UTILS_AVAILABLE,
        'logging_utils': _LOGGING_UTILS_AVAILABLE,
    }


def check_dependencies() -> Dict[str, bool]:
    """
    Vérifie la disponibilité des dépendances externes.
    
    Returns:
        Dict[str, bool]: Statut des dépendances externes
    """
    deps = {}
    
    # TOML parsing
    try:
        if hasattr(__builtins__, 'tomllib'):
            deps['tomllib'] = True
        else:
            import tomli
            deps['tomllib'] = True
    except ImportError:
        deps['tomllib'] = False
    
    # Packaging pour validation de versions
    try:
        import packaging
        deps['packaging'] = True
    except ImportError:
        deps['packaging'] = False
    
    # Colorama pour formatage coloré
    try:
        import colorama
        deps['colorama'] = True
    except ImportError:
        deps['colorama'] = False
    
    return deps


# Fonctions de commodité qui regroupent plusieurs utilitaires
def quick_validate_environment(name: str, python_version: str, 
                             project_path: Optional[Path] = None) -> List[str]:
    """
    Validation rapide d'un environnement.
    
    Args:
        name: Nom de l'environnement
        python_version: Version Python
        project_path: Chemin du projet (optionnel)
        
    Returns:
        Liste des erreurs de validation
    """
    errors = []
    
    if _VALIDATION_UTILS_AVAILABLE:
        if not validate_environment_name(name):
            errors.append(f"Nom d'environnement invalide: {name}")
        
        if not validate_python_version(python_version):
            errors.append(f"Version Python invalide: {python_version}")
        
        if project_path and not validate_project_structure(project_path):
            errors.append(f"Structure de projet invalide: {project_path}")
    else:
        logger.warning("Validation non disponible, validation sautée")
    
    return errors


def parse_project_file(project_path: Path) -> Optional[Any]:
    """
    Parse un fichier de projet (pyproject.toml, requirements.txt, etc.).
    
    Args:
        project_path: Chemin vers le fichier de projet
        
    Returns:
        Objet représentant le fichier parsé ou None
    """
    if not project_path.exists():
        return None
    
    if project_path.name == "pyproject.toml" and _PYPROJECT_PARSER_AVAILABLE:
        try:
            parser = PyProjectParser(project_path)
            return parser.parse_pyproject()
        except Exception as e:
            logger.error(f"Erreur parsing pyproject.toml: {e}")
            return None
    
    # Autres types de fichiers...
    logger.info(f"Type de fichier non supporté pour le parsing: {project_path.name}")
    return None


# Version du module utils
__version__ = "1.1.0"