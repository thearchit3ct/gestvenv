"""
Utilitaires pour GestVenv.

Ce package contient des modules utilitaires indépendants utilisés par les services et les composants core:
- path_utils: Fonctions de gestion des chemins
- system_utils: Fonctions d'interaction avec le système
- validation_utils: Fonctions de validation des entrées
- format_utils: Fonctions de formatage et d'affichage
- logging_utils: Fonctions de gestion des logs et de débogage
"""

# Définition des exports principaux pour simplifier les imports
from .path_utils import (
    get_os_name,
    expand_user_path,
    resolve_path,
    ensure_dir_exists,
    get_default_data_dir,
    get_normalized_path,
    get_relative_path,
    is_subpath,
    find_file_in_parents,
    get_file_extension,
    get_file_name_without_extension,
    split_path
)

from .system_utils import (
    run_simple_command,
    get_current_username,
    is_command_available,
    get_terminal_size,
    get_python_version_info,
    get_system_info,
    check_program_version,
    open_file,
    get_free_disk_space
)

from .validation_utils import (
    is_valid_name,
    is_valid_path,
    is_safe_directory,
    matches_pattern,
    parse_version_string,
    is_valid_python_version,
    is_valid_package_name,
    validate_packages_list,
    parse_key_value_string
)

from .format_utils import (
    format_timestamp,
    truncate_string,
    format_list_as_table,
    get_color_for_terminal,
    format_size,
    format_duration
)

from .logging_utils import (
    setup_logging,
    get_logger,
    get_log_manager,
    log_operation,
    log_package_operation,
    log_error,
    LogLevel,
    LogCategory,
    LoggedOperation,
    GestVenvLogManager,
    ColoredFormatter,
    StructuredFormatter
)

__all__ = [
    # path_utils
    'get_os_name', 'expand_user_path', 'resolve_path', 'ensure_dir_exists',
    'get_default_data_dir', 'get_normalized_path', 'get_relative_path',
    'is_subpath', 'find_file_in_parents', 'get_file_extension',
    'get_file_name_without_extension', 'split_path',
    
    # system_utils
    'run_simple_command', 'get_current_username', 'is_command_available', 
    'get_terminal_size', 'get_python_version_info', 'get_system_info',
    'check_program_version', 'open_file', 'get_free_disk_space',
    
    # validation_utils
    'is_valid_name', 'is_valid_path', 'is_safe_directory', 
    'matches_pattern', 'parse_version_string', 'is_valid_python_version',
    'is_valid_package_name', 'validate_packages_list', 'parse_key_value_string',
    
    # format_utils
    'format_timestamp', 'truncate_string', 'format_list_as_table',
    'get_color_for_terminal', 'format_size', 'format_duration',
    
    # logging_utils
    'setup_logging', 'get_logger', 'get_log_manager', 'log_operation',
    'log_package_operation', 'log_error', 'LogLevel', 'LogCategory',
    'LoggedOperation', 'GestVenvLogManager', 'ColoredFormatter', 
    'StructuredFormatter'
]