"""
Utilitaires pour GestVenv.

Ce package contient des modules utilitaires indépendants utilisés par les services et les composants core:
- path_utils: Fonctions de gestion des chemins
- system_utils: Fonctions d'interaction avec le système
- validation_utils: Fonctions de validation des entrées
- format_utils: Fonctions de formatage et d'affichage
"""

# Définition des exports principaux pour simplifier les imports
from .path_utils import (
    get_os_name,
    expand_user_path,
    resolve_path,
    ensure_dir_exists,
    get_default_data_dir,
    get_normalized_path
)

from .system_utils import (
    run_simple_command,
    get_current_username,
    is_command_available,
    get_terminal_size
)

from .validation_utils import (
    is_valid_name,
    is_valid_path,
    is_safe_directory,
    matches_pattern,
    parse_version_string
)

from .format_utils import (
    format_timestamp,
    truncate_string,
    format_list_as_table,
    get_color_for_terminal
)

__all__ = [
    # path_utils
    'get_os_name', 'expand_user_path', 'resolve_path', 'ensure_dir_exists',
    'get_default_data_dir', 'get_normalized_path',
    
    # system_utils
    'run_simple_command', 'get_current_username', 'is_command_available', 
    'get_terminal_size',
    
    # validation_utils
    'is_valid_name', 'is_valid_path', 'is_safe_directory', 
    'matches_pattern', 'parse_version_string',
    
    # format_utils
    'format_timestamp', 'truncate_string', 'format_list_as_table',
    'get_color_for_terminal'
]