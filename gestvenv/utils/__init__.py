"""
Package utils pour GestVenv v1.1
Utilitaires centralisés pour la gestion moderne des environnements Python.
"""

from .path_utils import PathUtils, normalize_path, safe_path_join
from .system_utils import SystemUtils, get_system_info, check_command_available
from .format_utils import FormatUtils, format_size, format_duration, format_table
from .validation_utils import ValidationUtils, validate_package_name, validate_version
from .toml_utils import TomlUtils, load_toml, save_toml, validate_toml_structure
from .pyproject_parser import PyProjectParser, PyProjectConfig, ProjectMetadata
from .migration_utils import MigrationService, MigrationAnalysis, RequirementsConverter
from .logging_utils import LoggingUtils, setup_logging, get_logger

__version__ = "1.1.0"
__all__ = [
    # Path utilities
    "PathUtils", "normalize_path", "safe_path_join",
    # System utilities  
    "SystemUtils", "get_system_info", "check_command_available",
    # Format utilities
    "FormatUtils", "format_size", "format_duration", "format_table",
    # Validation utilities
    "ValidationUtils", "validate_package_name", "validate_version",
    # TOML utilities
    "TomlUtils", "load_toml", "save_toml", "validate_toml_structure",
    # PyProject utilities
    "PyProjectParser", "PyProjectConfig", "ProjectMetadata",
    # Migration utilities
    "MigrationService", "MigrationAnalysis", "RequirementsConverter",
    # Logging utilities
    "LoggingUtils", "setup_logging", "get_logger",
]