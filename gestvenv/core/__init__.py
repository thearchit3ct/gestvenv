"""
Module core de GestVenv v1.1

Ce module contient les composants centraux du système :
- Modèles de données
- Gestionnaire d'environnements
- Gestionnaire de configuration
- Exceptions personnalisées
"""

from .models import (
    EnvironmentInfo,
    PyProjectInfo,
    PackageInfo,
    Config,
    EnvironmentResult,
    InstallResult,
    SyncResult,
    DiagnosticReport,
    DiagnosticIssue,
    OptimizationSuggestion,
    ProjectTemplate,
    TemplateFile,
    CommandResult,
    ExportResult,
    ActivationResult,
    RepairResult,
    EnvironmentHealth,
    BackendType,
    SourceFileType,
    ExportFormat,
    IssueLevel,
)

from .environment_manager import EnvironmentManager
from .config_manager import ConfigManager
from .exceptions import (
    GestVenvError,
    EnvironmentError,
    BackendError,
    ConfigurationError,
    ValidationError,
    SecurityValidationError,
    MigrationError,
    CacheError,
    TemplateError,
    DiagnosticError,
)

__all__ = [
    # Models
    "EnvironmentInfo",
    "PyProjectInfo", 
    "PackageInfo",
    "Config",
    "EnvironmentResult",
    "InstallResult",
    "SyncResult",
    "DiagnosticReport",
    "DiagnosticIssue",
    "OptimizationSuggestion",
    "ProjectTemplate",
    "TemplateFile",
    "CommandResult",
    "ExportResult",
    "ActivationResult",
    "RepairResult",
    
    # Enums
    "EnvironmentHealth",
    "BackendType",
    "SourceFileType",
    "ExportFormat",
    "IssueLevel",
    
    # Managers
    "EnvironmentManager",
    "ConfigManager",
    
    # Exceptions
    "GestVenvError",
    "EnvironmentError",
    "BackendError",
    "ConfigurationError",
    "ValidationError",
    "SecurityValidationError",
    "MigrationError",
    "CacheError",
    "TemplateError",
    "DiagnosticError",
]

# Version du module core
__version__ = "1.1.0"