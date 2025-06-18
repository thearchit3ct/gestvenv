# API Core - GestVenv v1.1

Module central de GestVenv contenant les composants fondamentaux du système.

## Vue d'ensemble

Le module `gestvenv.core` fournit :
- **Models** : Structures de données et enums
- **EnvironmentManager** : Gestionnaire principal des environnements
- **ConfigManager** : Gestion de la configuration
- **Exceptions** : Hiérarchie d'exceptions personnalisées

## Models

### Classes principales

#### EnvironmentInfo
```python
@dataclass
class EnvironmentInfo:
    name: str
    path: Path
    python_version: str
    packages: List[PackageInfo]
    backend_type: BackendType
    created_at: float
    updated_at: float
    pyproject_info: Optional[PyProjectInfo] = None
    lock_file_path: Optional[Path] = None
    health_status: EnvironmentHealth = EnvironmentHealth.UNKNOWN
```

#### PackageInfo
```python
@dataclass
class PackageInfo:
    name: str
    version: str
    summary: Optional[str] = None
    homepage: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    installed_via: Optional[str] = None
```

#### Config
```python
@dataclass
class Config:
    home_dir: Path
    environments_dir: Path
    cache_dir: Path
    preferred_backend: str = "auto"
    cache_enabled: bool = True
    cache_size_mb: int = 2048
    parallel_downloads: int = 4
    offline_mode: bool = False
    auto_cleanup: bool = True
    security_checks: bool = True
```

### Results et Enums

#### BackendType
```python
class BackendType(Enum):
    PIP = "pip"
    UV = "uv"
    POETRY = "poetry"
    PDM = "pdm"
    AUTO = "auto"
```

#### EnvironmentHealth
```python
class EnvironmentHealth(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"
```

#### EnvironmentResult
```python
@dataclass
class EnvironmentResult:
    success: bool
    message: str
    environment_info: Optional[EnvironmentInfo] = None
    details: Dict[str, Any] = field(default_factory=dict)
    execution_time: Optional[float] = None
```

## EnvironmentManager

Gestionnaire principal des environnements virtuels avec services intégrés.

### Initialisation
```python
def __init__(self, config_manager: Optional[ConfigManager] = None):
    self.config_manager = config_manager or ConfigManager()
```

### Gestion des environnements

#### create_environment
```python
def create_environment(
    self, 
    name: str, 
    python_version: Optional[str] = None,
    backend: Optional[str] = None,
    template: Optional[str] = None
) -> EnvironmentResult:
```
Crée un nouvel environnement virtuel avec template optionnel.

#### delete_environment  
```python
def delete_environment(self, name: str, force: bool = False) -> EnvironmentResult:
```
Supprime un environnement avec sauvegarde optionnelle.

#### list_environments
```python
def list_environments(self) -> List[EnvironmentInfo]:
```
Liste tous les environnements disponibles.

#### activate_environment
```python
def activate_environment(self, name: str) -> ActivationResult:
```
Active un environnement et retourne les variables d'environnement.

### Gestion des packages

#### install_package
```python
def install_package(
    self, 
    env_name: str, 
    package: str,
    **kwargs
) -> InstallResult:
```
Installe un package via le service unifié.

#### sync_environment
```python
def sync_environment(
    self, 
    env_name: str,
    source: Optional[Path] = None
) -> SyncResult:
```
Synchronise un environnement depuis pyproject.toml ou requirements.txt.

### Import/Export

#### export_environment
```python
def export_environment(
    self, 
    name: str, 
    format: ExportFormat,
    output_path: Optional[Path] = None
) -> ExportResult:
```
Exporte un environnement vers différents formats.

#### import_from_file
```python
def import_from_file(
    self, 
    source: Path, 
    target_name: str
) -> EnvironmentResult:
```
Importe un environnement depuis un fichier de configuration.

### Diagnostic

#### doctor_environment
```python
def doctor_environment(self, name: Optional[str] = None) -> DiagnosticReport:
```
Diagnostic complet d'un environnement ou du système.

### Propriétés (Lazy Loading)

#### backend_manager
```python
@property
def backend_manager(self) -> BackendManager:
```

#### package_service
```python
@property  
def package_service(self) -> PackageService:
```

#### cache_service
```python
@property
def cache_service(self) -> CacheService:
```

#### migration_service
```python
@property
def migration_service(self) -> MigrationService:
```

#### diagnostic_service
```python
@property
def diagnostic_service(self) -> DiagnosticService:
```

## ConfigManager

Gestionnaire de configuration avec validation et mise à jour automatique.

### Méthodes principales

#### load_config
```python
def load_config(self) -> Config:
```
Charge la configuration depuis les fichiers système et utilisateur.

#### save_config  
```python
def save_config(self, config: Optional[Config] = None) -> bool:
```
Sauvegarde la configuration actuelle.

#### update_config
```python
def update_config(self, **updates) -> bool:
```
Met à jour des valeurs spécifiques de configuration.

#### validate_config
```python
def validate_config(self, config: Optional[Config] = None) -> List[str]:
```
Valide la configuration et retourne les erreurs.

#### reset_to_defaults
```python
def reset_to_defaults(self) -> bool:
```
Remet la configuration aux valeurs par défaut.

## Exceptions

### Hiérarchie

```
GestVenvError (base)
├── EnvironmentError
│   ├── EnvironmentNotFoundError
│   └── EnvironmentExistsError
├── BackendError
│   ├── BackendNotAvailableError
│   └── PackageInstallationError
├── ConfigurationError
├── ValidationError
│   ├── SecurityValidationError
│   ├── PyProjectParsingError
│   └── RequirementsParsingError
├── MigrationError
├── CacheError
├── TemplateError
└── DiagnosticError
```

### Classes d'exceptions

#### GestVenvError
```python
class GestVenvError(Exception):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
```

#### EnvironmentError
```python
class EnvironmentError(GestVenvError):
    def __init__(self, message: str, environment_name: Optional[str] = None, 
                 details: Optional[Dict[str, Any]] = None):
        self.environment_name = environment_name
```

#### BackendError
```python
class BackendError(GestVenvError):
    def __init__(self, message: str, backend_name: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        self.backend_name = backend_name
```

#### ValidationError
```python
class ValidationError(GestVenvError):
    def __init__(self, message: str, field_name: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        self.field_name = field_name
```

### Exceptions spécialisées

#### PackageInstallationError
```python
class PackageInstallationError(BackendError):
    def __init__(self, message: str, package_name: str, backend_name: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        self.package_name = package_name
```

#### PyProjectParsingError
```python
class PyProjectParsingError(ValidationError):
    def __init__(self, message: str, file_path: Optional[str] = None,
                 line_number: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        self.file_path = file_path
        self.line_number = line_number
```

## Usage Examples

### Création d'environnement
```python
from gestvenv.core import EnvironmentManager

manager = EnvironmentManager()
result = manager.create_environment(
    name="monprojet",
    python_version="3.11",
    backend="uv",
    template="web"
)

if result.success:
    print(f"Environnement créé : {result.environment_info.path}")
```

### Installation de packages
```python
install_result = manager.install_package("monprojet", "fastapi[all]")
if install_result.success:
    print(f"Packages installés : {install_result.packages_installed}")
```

### Diagnostic
```python
report = manager.doctor_environment("monprojet")
print(f"Santé : {report.overall_status}")
for issue in report.issues:
    print(f"- {issue.level}: {issue.description}")
```
