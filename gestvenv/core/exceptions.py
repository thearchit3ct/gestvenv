"""
Exceptions personnalisées pour GestVenv v1.1

Hiérarchie des exceptions :
- GestVenvError (base)
  ├── EnvironmentError (environnements)
  ├── BackendError (backends)
  ├── ConfigurationError (configuration)
  ├── ValidationError (validation)
  ├── SecurityValidationError (sécurité)
  ├── MigrationError (migration)
  ├── CacheError (cache)
  ├── TemplateError (templates)
  └── DiagnosticError (diagnostic)
"""

from typing import Optional, Dict, Any, List


class GestVenvError(Exception):
    """Exception de base pour toutes les erreurs GestVenv"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (details: {self.details})"
        return self.message


class EnvironmentError(GestVenvError):
    """Erreurs liées aux environnements virtuels"""
    
    def __init__(self, message: str, environment_name: Optional[str] = None, 
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.environment_name = environment_name


class BackendError(GestVenvError):
    """Erreurs liées aux backends de packages"""
    
    def __init__(self, message: str, backend_name: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.backend_name = backend_name


class ConfigurationError(GestVenvError):
    """Erreurs de configuration"""
    
    def __init__(self, message: str, config_path: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.config_path = config_path


class ValidationError(GestVenvError):
    """Erreurs de validation des données"""
    
    def __init__(self, message: str, field: Optional[str] = None,
                 validation_errors: Optional[List[str]] = None,
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.field = field
        self.validation_errors = validation_errors or []


class SecurityValidationError(ValidationError):
    """Erreurs de validation de sécurité"""
    
    def __init__(self, message: str, security_issues: Optional[List[str]] = None,
                 field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, field, security_issues, details)
        self.security_issues = security_issues or []


class MigrationError(GestVenvError):
    """Erreurs lors des migrations"""
    
    def __init__(self, message: str, from_version: Optional[str] = None,
                 to_version: Optional[str] = None, migration_step: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.from_version = from_version
        self.to_version = to_version
        self.migration_step = migration_step


class CacheError(GestVenvError):
    """Erreurs du système de cache"""
    
    def __init__(self, message: str, cache_operation: Optional[str] = None,
                 package_name: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.cache_operation = cache_operation
        self.package_name = package_name


class TemplateError(GestVenvError):
    """Erreurs liées aux templates de projets"""
    
    def __init__(self, message: str, template_name: Optional[str] = None,
                 template_file: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.template_name = template_name
        self.template_file = template_file


class DiagnosticError(GestVenvError):
    """Erreurs lors des diagnostics"""
    
    def __init__(self, message: str, diagnostic_type: Optional[str] = None,
                 environment_name: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.diagnostic_type = diagnostic_type
        self.environment_name = environment_name


class BackendNotAvailableError(BackendError):
    """Backend non disponible sur le système"""
    pass


class EnvironmentNotFoundError(EnvironmentError):
    """Environnement introuvable"""
    pass


class EnvironmentExistsError(EnvironmentError):
    """Environnement existe déjà"""
    pass


class PackageInstallationError(BackendError):
    """Erreur d'installation de package"""
    
    def __init__(self, message: str, package_name: str, backend_name: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message, backend_name, details)
        self.package_name = package_name


class PyProjectParsingError(ValidationError):
    """Erreur de parsing de pyproject.toml"""
    
    def __init__(self, message: str, file_path: Optional[str] = None,
                 line_number: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details=details)
        self.file_path = file_path
        self.line_number = line_number


class RequirementsParsingError(ValidationError):
    """Erreur de parsing de requirements.txt"""
    
    def __init__(self, message: str, file_path: Optional[str] = None,
                 line_number: Optional[int] = None, line_content: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details=details)
        self.file_path = file_path
        self.line_number = line_number
        self.line_content = line_content