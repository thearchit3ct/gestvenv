# API Backends - GestVenv v1.1

Système de backends modulaires pour la gestion des packages Python avec abstraction unifiée.

## Vue d'ensemble

Le module `gestvenv.backends` fournit une abstraction unifiée pour différents gestionnaires de packages :
- **PackageBackend** : Interface abstraite commune
- **PipBackend** : Backend pip classique 
- **UvBackend** : Backend uv haute performance
- **PoetryBackend** : Backend Poetry (futur)
- **PDMBackend** : Backend PDM (futur)
- **BackendManager** : Sélection et gestion des backends

## Architecture

### Interface commune

Tous les backends implémentent l'interface `PackageBackend` pour une utilisation transparente par les services.

### Sélection automatique

Le `BackendManager` sélectionne automatiquement le backend optimal selon :
- Disponibilité sur le système
- Type de projet détecté
- Performance requise
- Configuration utilisateur

## PackageBackend (Interface abstraite)

Interface de base définissant les opérations communes à tous les backends.

### Propriétés abstraites

```python
@property
@abstractmethod
def name(self) -> str:
    """Nom du backend"""

@property  
@abstractmethod
def available(self) -> bool:
    """Disponibilité sur le système"""

@property
@abstractmethod
def capabilities(self) -> BackendCapabilities:
    """Capacités supportées"""

@property
@abstractmethod
def performance_score(self) -> int:
    """Score de performance (0-100)"""
```

### Méthodes abstraites

#### Gestion des environnements
```python
@abstractmethod
def create_environment(self, path: Path, python_version: str) -> bool:
    """Création d'environnement virtuel"""

@abstractmethod  
def activate_environment(self, env_path: Path) -> Dict[str, str]:
    """Variables d'activation d'environnement"""
```

#### Gestion des packages
```python
@abstractmethod
def install_package(self, env_path: Path, package: str, **kwargs) -> InstallResult:
    """Installation de package"""

@abstractmethod
def uninstall_package(self, env_path: Path, package: str) -> bool:
    """Désinstallation de package"""

@abstractmethod
def list_packages(self, env_path: Path) -> List[PackageInfo]:
    """Liste des packages installés"""
```

#### Fichiers de configuration
```python
@abstractmethod
def install_from_requirements(self, env_path: Path, req_path: Path) -> bool:
    """Installation depuis requirements.txt"""

@abstractmethod  
def freeze_requirements(self, env_path: Path) -> str:
    """Génération requirements.txt"""
```

### BackendCapabilities

Structure décrivant les capacités d'un backend :

```python
@dataclass
class BackendCapabilities:
    supports_lock_files: bool = False
    supports_dependency_groups: bool = False
    supports_parallel_install: bool = False
    supports_editable_installs: bool = True
    supports_workspace: bool = False
    supports_pyproject_sync: bool = False
    supported_formats: List[str] = field(default_factory=list)
    max_parallel_jobs: int = 1
```

## PipBackend

Backend classique utilisant pip avec compatibilité universelle.

### Caractéristiques
- **Performance** : Score 60/100
- **Compatibilité** : Universelle
- **Lock files** : Via pip-tools (optionnel)
- **Installation parallèle** : Non supportée nativement

### Implémentation

#### Installation de packages
```python
def install_package(self, env_path: Path, package: str, **kwargs) -> InstallResult:
    """Installation via pip avec options avancées"""
    pip_executable = self._get_pip_executable(env_path)
    
    cmd = [
        str(pip_executable), "install",
        "--no-input", "--disable-pip-version-check"
    ]
    
    # Options spécifiques
    if kwargs.get("upgrade", False):
        cmd.append("--upgrade")
    if kwargs.get("no_deps", False):
        cmd.append("--no-deps")
    if kwargs.get("editable", False):
        cmd.extend(["-e", package])
    else:
        cmd.append(package)
        
    # Exécution avec capture
    result = self._execute_command(cmd)
    return InstallResult(
        success=result.returncode == 0,
        message=result.stdout or result.stderr,
        packages_installed=[package] if result.returncode == 0 else [],
        backend_used="pip"
    )
```

#### Gestion des requirements
```python
def install_from_requirements(self, env_path: Path, req_path: Path) -> bool:
    """Installation depuis requirements.txt"""
    pip_executable = self._get_pip_executable(env_path)
    cmd = [str(pip_executable), "install", "-r", str(req_path)]
    result = self._execute_command(cmd)
    return result.returncode == 0

def freeze_requirements(self, env_path: Path) -> str:
    """Génération du freeze pip"""
    pip_executable = self._get_pip_executable(env_path)
    cmd = [str(pip_executable), "freeze", "--local"]
    result = self._execute_command(cmd)
    return result.stdout if result.returncode == 0 else ""
```

### Capacités
```python
@property
def capabilities(self) -> BackendCapabilities:
    return BackendCapabilities(
        supports_lock_files=False,
        supports_dependency_groups=False,
        supports_parallel_install=False,
        supports_editable_installs=True,
        supports_workspace=False,
        supports_pyproject_sync=False,
        supported_formats=["requirements.txt"],
        max_parallel_jobs=1
    )
```

## UvBackend

Backend haute performance utilisant uv pour des installations ultra-rapides.

### Caractéristiques
- **Performance** : Score 95/100 (10x plus rapide que pip)
- **Lock files** : Support natif uv.lock
- **Installation parallèle** : Jusqu'à 8 jobs simultanés
- **PyProject.toml** : Support complet PEP 621

### Implémentation avancée

#### Installation optimisée
```python
def install_package(self, env_path: Path, package: str, **kwargs) -> InstallResult:
    """Installation ultra-rapide via uv"""
    start_time = time.time()
    
    cmd = ["uv", "pip", "install"]
    
    # Configuration environnement
    cmd.extend(["--python", str(env_path / "bin" / "python")])
    
    # Options performance
    if self.capabilities.supports_parallel_install:
        max_jobs = min(kwargs.get("max_jobs", 4), self.capabilities.max_parallel_jobs)
        cmd.extend(["--jobs", str(max_jobs)])
    
    # Cache uv intégré
    if not kwargs.get("no_cache", False):
        cmd.append("--cache-dir")
        cmd.append(str(self._get_cache_dir()))
    
    # Installation
    cmd.append(package)
    
    result = self._execute_command(cmd)
    execution_time = time.time() - start_time
    
    return InstallResult(
        success=result.returncode == 0,
        message=result.stdout or result.stderr,
        packages_installed=self._parse_installed_packages(result.stdout),
        backend_used="uv",
        execution_time=execution_time
    )
```

#### Support pyproject.toml
```python
def sync_from_pyproject(
    self, 
    env_path: Path, 
    pyproject_path: Path,
    groups: Optional[List[str]] = None
) -> bool:
    """Synchronisation depuis pyproject.toml"""
    cmd = [
        "uv", "pip", "sync",
        "--python", str(env_path / "bin" / "python"),
        str(pyproject_path)
    ]
    
    if groups:
        for group in groups:
            cmd.extend(["--group", group])
    
    result = self._execute_command(cmd)
    return result.returncode == 0

def create_lock_file(self, pyproject_path: Path) -> Path:
    """Création de uv.lock"""
    lock_path = pyproject_path.parent / "uv.lock"
    cmd = ["uv", "lock", "--project", str(pyproject_path.parent)]
    result = self._execute_command(cmd)
    
    if result.returncode == 0 and lock_path.exists():
        return lock_path
    raise BackendError("Échec création uv.lock")

def install_from_lock(self, env_path: Path, lock_path: Path) -> bool:
    """Installation depuis uv.lock"""
    cmd = [
        "uv", "pip", "install", 
        "--python", str(env_path / "bin" / "python"),
        "--requirement", str(lock_path)
    ]
    result = self._execute_command(cmd)
    return result.returncode == 0
```

### Capacités avancées
```python
@property
def capabilities(self) -> BackendCapabilities:
    return BackendCapabilities(
        supports_lock_files=True,
        supports_dependency_groups=True,
        supports_parallel_install=True,
        supports_editable_installs=True,
        supports_workspace=False,
        supports_pyproject_sync=True,
        supported_formats=["pyproject.toml", "requirements.txt", "uv.lock"],
        max_parallel_jobs=8
    )
```

## PoetryBackend (Futur)

Backend Poetry pour gestion complète de projets avec publication.

### Caractéristiques prévues
- **Performance** : Score 80/100
- **Lock files** : poetry.lock détaillé
- **Workspace** : Support des mono-repos
- **Publication** : Intégration PyPI

### Interface future
```python
def sync_poetry_project(self, env_path: Path) -> bool:
    """Synchronisation projet Poetry"""

def manage_poetry_groups(self, env_path: Path, groups: List[str]) -> bool:
    """Gestion des groupes de dépendances Poetry"""

def publish_package(self, project_path: Path, repository: str = "pypi") -> bool:
    """Publication sur PyPI"""
```

## PDMBackend (Futur)

Backend PDM avec support PEP 582 (sans environnements virtuels).

### Caractéristiques prévues
- **Performance** : Score 85/100
- **PEP 582** : Installation directe sans venv
- **Standards** : Respect complet des PEPs modernes

### Interface future
```python
def sync_pdm_project(self, env_path: Path) -> bool:
    """Synchronisation projet PDM"""

def manage_pdm_groups(self, env_path: Path, groups: List[str]) -> bool:
    """Gestion des groupes PDM"""
```

## BackendManager

Gestionnaire central de sélection et configuration des backends.

### Initialisation
```python
def __init__(self, config: Config):
    self.config = config
    self.backends: Dict[str, PackageBackend] = {}
    self.preferred_backend = config.preferred_backend
    self.initialize_backends()
```

### Sélection de backend

#### get_backend
```python
def get_backend(
    self, 
    preference: str, 
    env_info: Optional[EnvironmentInfo] = None
) -> PackageBackend:
    """Sélection du backend optimal"""
    if preference == "auto":
        return self._select_optimal_backend(env_info)
    elif preference in self.backends and self.backends[preference].available:
        return self.backends[preference]
    else:
        return self._get_fallback_backend()
```

#### Sélection automatique
```python
def _select_optimal_backend(self, env_info: Optional[EnvironmentInfo]) -> PackageBackend:
    """Algorithme de sélection intelligent"""
    # Priorité aux lock files existants
    if env_info and env_info.lock_file_path:
        if env_info.lock_file_path.name == "uv.lock" and self.backends['uv'].available:
            return self.backends['uv']
        elif env_info.lock_file_path.name == "poetry.lock" and self.backends['poetry'].available:
            return self.backends['poetry']
    
    # Détection basée sur pyproject.toml
    if env_info and env_info.pyproject_info:
        detected = self.detect_project_backend(env_info.pyproject_info.source_path.parent)
        if detected != "auto" and self.backends[detected].available:
            return self.backends[detected]
    
    # Sélection par performance
    priority_order = ['uv', 'poetry', 'pdm', 'pip']
    for backend_name in priority_order:
        backend = self.backends.get(backend_name)
        if backend and backend.available:
            return backend
    
    raise BackendError("Aucun backend disponible")
```

### Détection de projet

#### detect_project_backend
```python
def detect_project_backend(self, project_path: Path) -> str:
    """Détection automatique du backend optimal"""
    # Fichiers de lock
    if (project_path / "uv.lock").exists():
        return "uv"
    elif (project_path / "poetry.lock").exists():
        return "poetry"
    elif (project_path / "pdm.lock").exists():
        return "pdm"
    
    # Analyse pyproject.toml
    pyproject_path = project_path / "pyproject.toml"
    if pyproject_path.exists():
        detected = self._detect_pyproject_backend(pyproject_path)
        if detected:
            return detected
    
    # requirements.txt → pip
    if (project_path / "requirements.txt").exists():
        return "pip"
    
    return "auto"
```

#### Détection pyproject.toml
```python
def _detect_pyproject_backend(self, pyproject_path: Path) -> Optional[str]:
    """Analyse des sections [tool.*] pour détection"""
    from ..utils import TomlHandler
    
    data = TomlHandler.load(pyproject_path)
    tool_sections = data.get('tool', {})
    
    # Détection par sections spécifiques
    if 'poetry' in tool_sections:
        return 'poetry'
    elif 'pdm' in tool_sections:
        return 'pdm'
    elif 'uv' in tool_sections:
        return 'uv'
    
    # PEP 621 standard → uv par défaut
    if 'project' in data:
        return 'uv'
    
    return None
```

### Informations et statistiques

#### list_available_backends
```python
def list_available_backends(self) -> List[str]:
    """Liste des backends disponibles"""
    return [name for name, backend in self.backends.items() if backend.available]

def get_backend_info(self) -> Dict[str, Any]:
    """Informations détaillées de tous les backends"""
    info = {}
    for name, backend in self.backends.items():
        info[name] = {
            'available': backend.available,
            'version': backend.version if backend.available else None,
            'performance_score': backend.performance_score,
            'capabilities': asdict(backend.capabilities),
            'path': getattr(backend, 'executable_path', None)
        }
    return info
```

### Configuration

#### set_preferred_backend
```python
def set_preferred_backend(self, backend: str) -> bool:
    """Configuration du backend préféré"""
    if backend in self.backends or backend == "auto":
        self.preferred_backend = backend
        self.config.preferred_backend = backend
        return True
    return False
```

## Usage Examples

### Sélection automatique
```python
from gestvenv.backends import BackendManager
from gestvenv.core import ConfigManager

config_manager = ConfigManager()
backend_manager = BackendManager(config_manager.config)

# Sélection automatique
backend = backend_manager.get_backend("auto", env_info)
print(f"Backend sélectionné: {backend.name}")

# Installation avec backend optimal
result = backend.install_package(env_path, "fastapi[all]")
```

### Détection de projet
```python
project_path = Path("/path/to/project")
detected_backend = backend_manager.detect_project_backend(project_path)
print(f"Backend détecté: {detected_backend}")

# Utilisation du backend détecté
backend = backend_manager.get_backend(detected_backend)
```

### Informations backends
```python
available = backend_manager.list_available_backends()
print(f"Backends disponibles: {available}")

info = backend_manager.get_backend_info()
for name, details in info.items():
    print(f"{name}: {details['performance_score']}/100")
```

### Installation avec options
```python
# Installation avec uv et parallélisation
uv_backend = backend_manager.backends['uv']
if uv_backend.available:
    result = uv_backend.install_package(
        env_path, 
        "django>=4.2",
        max_jobs=8,
        upgrade=True
    )
    print(f"Durée: {result.execution_time:.2f}s")
```