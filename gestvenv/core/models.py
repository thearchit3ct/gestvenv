"""
Modèles de données pour GestVenv v1.1
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import json
import re

from packaging import version


class EnvironmentHealth(Enum):
    """États de santé d'un environnement"""
    HEALTHY = "healthy"
    NEEDS_UPDATE = "needs_update"
    HAS_WARNINGS = "has_warnings"
    HAS_ERRORS = "has_errors"
    CORRUPTED = "corrupted"
    UNKNOWN = "unknown"


class BackendType(Enum):
    """Types de backends supportés"""
    PIP = "pip"
    UV = "uv"
    POETRY = "poetry"
    PDM = "pdm"
    AUTO = "auto"


class SourceFileType(Enum):
    """Types de fichiers sources supportés"""
    REQUIREMENTS_TXT = "requirements.txt"
    PYPROJECT_TOML = "pyproject.toml"
    SETUP_PY = "setup.py"
    POETRY_LOCK = "poetry.lock"
    UV_LOCK = "uv.lock"
    ENVIRONMENT_YML = "environment.yml"


class ExportFormat(Enum):
    """Formats d'export supportés"""
    REQUIREMENTS = "requirements"
    PYPROJECT = "pyproject"
    JSON = "json"
    YAML = "yaml"
    POETRY = "poetry"
    CONDA = "conda"


class IssueLevel(Enum):
    """Niveaux de problèmes diagnostiques"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class PackageInfo:
    """Informations sur un package installé"""
    name: str
    version: str
    source: str = "pypi"
    is_editable: bool = False
    local_path: Optional[Path] = None
    backend_used: str = "pip"
    installed_at: datetime = field(default_factory=datetime.now)
    summary: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    requires: List[str] = field(default_factory=list)
    
    def compare_version(self, other: str) -> int:
        """Compare avec une autre version (-1, 0, 1)"""
        try:
            v1 = version.parse(self.version)
            v2 = version.parse(other)
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
            return 0
        except Exception:
            return 0
    
    def is_compatible(self, python_version: str) -> bool:
        """Vérifie la compatibilité Python"""
        # Logique simplifiée - peut être étendue
        return True
    
    def get_install_command(self) -> str:
        """Génère la commande d'installation"""
        if self.is_editable and self.local_path:
            return f"-e {self.local_path}"
        return f"{self.name}=={self.version}"
    
    def is_development_package(self) -> bool:
        """Indique si c'est un package de développement"""
        dev_keywords = ['test', 'dev', 'debug', 'lint', 'format', 'coverage', 'mock']
        return any(keyword in self.name.lower() for keyword in dev_keywords)


@dataclass
class PyProjectInfo:
    """Informations pyproject.toml (PEP 621)"""
    name: str
    version: str = "0.1.0"
    description: Optional[str] = None
    readme: Optional[str] = None
    requires_python: Optional[str] = None
    authors: List[Dict[str, str]] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    classifiers: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    optional_dependencies: Dict[str, List[str]] = field(default_factory=dict)
    urls: Dict[str, str] = field(default_factory=dict)
    scripts: Dict[str, str] = field(default_factory=dict)
    build_system: Dict[str, Any] = field(default_factory=dict)
    tool_sections: Dict[str, Any] = field(default_factory=dict)
    source_path: Optional[Path] = None
    
    def validate_pep621(self) -> bool:
        """Valide la conformité PEP 621"""
        required_fields = ['name', 'version']
        return all(getattr(self, field) for field in required_fields)
    
    def extract_dependencies(self, groups: Optional[List[str]] = None) -> List[str]:
        """Extrait les dépendances pour les groupes spécifiés"""
        deps = self.dependencies.copy()
        
        if groups:
            for group in groups:
                if group in self.optional_dependencies:
                    deps.extend(self.optional_dependencies[group])
        
        return deps
    
    def merge_dependencies(self, other: 'PyProjectInfo') -> 'PyProjectInfo':
        """Fusionne avec un autre PyProjectInfo"""
        merged = PyProjectInfo(
            name=self.name,
            version=self.version,
            description=self.description,
            dependencies=list(set(self.dependencies + other.dependencies))
        )
        
        # Fusion des dépendances optionnelles
        for group, deps in other.optional_dependencies.items():
            if group in merged.optional_dependencies:
                merged.optional_dependencies[group] = list(
                    set(merged.optional_dependencies[group] + deps)
                )
            else:
                merged.optional_dependencies[group] = deps.copy()
        
        return merged
    
    def to_requirements_txt(self, include_optional: bool = False) -> str:
        """Export vers format requirements.txt"""
        lines = self.dependencies.copy()
        
        if include_optional:
            for group_deps in self.optional_dependencies.values():
                lines.extend(group_deps)
        
        return '\n'.join(lines)
    
    def get_dependency_groups(self) -> List[str]:
        """Liste des groupes de dépendances optionnelles"""
        return list(self.optional_dependencies.keys())
    
    def has_build_system(self) -> bool:
        """Indique si un build system est défini"""
        return bool(self.build_system)


@dataclass
class EnvironmentInfo:
    """Informations complètes sur un environnement"""
    name: str
    path: Path
    python_version: str
    backend_type: BackendType = BackendType.AUTO
    source_file_type: SourceFileType = SourceFileType.REQUIREMENTS_TXT
    pyproject_info: Optional[PyProjectInfo] = None
    packages: List[PackageInfo] = field(default_factory=list)
    dependency_groups: Dict[str, List[str]] = field(default_factory=dict)
    lock_file_path: Optional[Path] = None
    health: EnvironmentHealth = EnvironmentHealth.UNKNOWN
    is_active: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> bool:
        """Valide la cohérence des informations"""
        return (self.name and 
                self.path.exists() and
                self.python_version and
                re.match(r'^\d+\.\d+', self.python_version))
    
    def to_dict(self) -> Dict[str, Any]:
        """Sérialise en dictionnaire"""
        return {
            'name': self.name,
            'path': str(self.path),
            'python_version': self.python_version,
            'backend_type': self.backend_type.value,
            'source_file_type': self.source_file_type.value,
            'pyproject_info': self.pyproject_info.__dict__ if self.pyproject_info else None,
            'packages': [pkg.__dict__ for pkg in self.packages],
            'dependency_groups': self.dependency_groups,
            'lock_file_path': str(self.lock_file_path) if self.lock_file_path else None,
            'health': self.health.value,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_used': self.last_used.isoformat(),
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnvironmentInfo':
        """Désérialise depuis un dictionnaire"""
        env = cls(
            name=data['name'],
            path=Path(data['path']),
            python_version=data['python_version'],
            backend_type=BackendType(data.get('backend_type', 'auto')),
            source_file_type=SourceFileType(data.get('source_file_type', 'requirements.txt')),
            health=EnvironmentHealth(data.get('health', 'unknown')),
            is_active=data.get('is_active', False),
            dependency_groups=data.get('dependency_groups', {}),
            metadata=data.get('metadata', {})
        )
        
        # Dates
        if 'created_at' in data:
            env.created_at = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data:
            env.updated_at = datetime.fromisoformat(data['updated_at'])
        if 'last_used' in data:
            env.last_used = datetime.fromisoformat(data['last_used'])
        
        # PyProject info
        if data.get('pyproject_info'):
            env.pyproject_info = PyProjectInfo(**data['pyproject_info'])
        
        # Packages
        env.packages = [PackageInfo(**pkg) for pkg in data.get('packages', [])]
        
        # Lock file
        if data.get('lock_file_path'):
            env.lock_file_path = Path(data['lock_file_path'])
        
        return env
    
    def get_package_count(self) -> int:
        """Nombre de packages installés"""
        return len(self.packages)
    
    def get_size_mb(self) -> float:
        """Taille de l'environnement en MB"""
        try:
            if not self.path.exists():
                return 0.0
            total_size = sum(f.stat().st_size for f in self.path.rglob('*') if f.is_file())
            return total_size / (1024 * 1024)
        except Exception:
            return 0.0
    
    def needs_sync(self) -> bool:
        """Indique si une synchronisation est nécessaire"""
        if not self.pyproject_info:
            return False
        
        expected_packages = set(
            dep.split('>=')[0].split('==')[0].split('[')[0] 
            for dep in self.pyproject_info.dependencies
        )
        installed_packages = set(pkg.name for pkg in self.packages)
        
        return expected_packages != installed_packages


@dataclass
class Config:
    """Configuration centrale de GestVenv"""
    version: str = "1.1.0"
    auto_migrate: bool = True
    default_python_version: str = "3.11"
    environments_path: Path = field(default_factory=lambda: Path.home() / ".gestvenv" / "environments")
    preferred_backend: str = "auto"
    backend_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    cache_settings: Dict[str, Any] = field(default_factory=lambda: {
        "enabled": True,
        "max_size_mb": 1000,
        "cleanup_interval_days": 30,
        "compression": True
    })
    show_migration_hints: bool = True
    offline_mode: bool = False
    template_settings: Dict[str, Any] = field(default_factory=dict)
    max_parallel_jobs: int = 4

    @property
    def cache_enabled(self) -> bool:
        """Indique si le cache est activé"""
        return self.cache_settings.get("enabled", True)

    @cache_enabled.setter
    def cache_enabled(self, value: bool) -> None:
        """Définit l'état du cache"""
        self.cache_settings["enabled"] = value
    
    def save(self, path: Path) -> bool:
        """Sauvegarde la configuration"""
        try:
            config_dict = {
                'version': self.version,
                'auto_migrate': self.auto_migrate,
                'default_python_version': self.default_python_version,
                'environments_path': str(self.environments_path),
                'preferred_backend': self.preferred_backend,
                'backend_configs': self.backend_configs,
                'cache_settings': self.cache_settings,
                'show_migration_hints': self.show_migration_hints,
                'offline_mode': self.offline_mode,
                'template_settings': self.template_settings
            }
            
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2)
            return True
        except Exception:
            return False
    
    @classmethod
    def load(cls, path: Path) -> 'Config':
        """Charge la configuration"""
        if not path.exists():
            return cls()
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            config = cls()
            config.version = data.get('version', '1.1.0')
            config.auto_migrate = data.get('auto_migrate', True)
            config.default_python_version = data.get('default_python_version', '3.11')
            config.environments_path = Path(data.get('environments_path', 
                                                   Path.home() / ".gestvenv" / "environments"))
            config.preferred_backend = data.get('preferred_backend', 'auto')
            config.backend_configs = data.get('backend_configs', {})
            config.cache_settings = data.get('cache_settings', config.cache_settings)
            config.show_migration_hints = data.get('show_migration_hints', True)
            config.offline_mode = data.get('offline_mode', False)
            config.template_settings = data.get('template_settings', {})
            
            return config
        except Exception:
            return cls()
    
    def migrate_from_v1_0(self) -> bool:
        """Migration depuis v1.0"""
        # Logique de migration spécifique
        return True
    
    def get_cache_max_size(self) -> int:
        """Taille max du cache en MB"""
        return self.cache_settings.get('max_size_mb', 1000)
    
    def get_cleanup_interval(self) -> int:
        """Intervalle de nettoyage en jours"""
        return self.cache_settings.get('cleanup_interval_days', 30)


# Modèles de résultats
@dataclass
class EnvironmentResult:
    """Résultat d'opération sur environnement"""
    success: bool
    message: str
    environment: Optional[EnvironmentInfo] = None
    warnings: List[str] = field(default_factory=list)
    execution_time: float = 0.0


@dataclass
class InstallResult:
    """Résultat d'installation de packages"""
    success: bool
    message: str
    packages_installed: List[str] = field(default_factory=list)
    packages_failed: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    backend_used: str = "pip"
    lock_file_created: Optional[Path] = None


@dataclass
class SyncResult:
    """Résultat de synchronisation"""
    success: bool
    message: str
    packages_added: List[str] = field(default_factory=list)
    packages_removed: List[str] = field(default_factory=list)
    packages_updated: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    execution_time: float = 0.0


@dataclass
class DiagnosticIssue:
    """Problème diagnostique"""
    level: IssueLevel
    category: str
    description: str
    solution: Optional[str] = None
    auto_fixable: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationSuggestion:
    """Suggestion d'optimisation"""
    category: str
    description: str
    command: str
    impact_score: float
    safe_to_apply: bool


@dataclass
class DiagnosticReport:
    """Rapport de diagnostic"""
    overall_status: EnvironmentHealth = EnvironmentHealth.UNKNOWN
    issues: List[DiagnosticIssue] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[OptimizationSuggestion] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    generated_at: datetime = field(default_factory=datetime.now)
    
    def get_critical_issues(self) -> List[DiagnosticIssue]:
        """Issues critiques"""
        return [issue for issue in self.issues if issue.level == IssueLevel.CRITICAL]
    
    def get_fixable_issues(self) -> List[DiagnosticIssue]:
        """Issues réparables automatiquement"""
        return [issue for issue in self.issues if issue.auto_fixable]


@dataclass
class TemplateFile:
    """Fichier de template"""
    path: str
    content: str
    is_template: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProjectTemplate:
    """Template de projet"""
    name: str
    description: str
    version: str
    default_params: Dict[str, Any] = field(default_factory=dict)
    files: List[TemplateFile] = field(default_factory=list)
    pyproject_template: Optional[PyProjectInfo] = None
    
    def validate(self) -> bool:
        """Valide le template"""
        return bool(self.name and self.description)
    
    def render(self, params: Dict[str, Any]) -> Dict[str, str]:
        """Rend le template avec paramètres"""
        rendered = {}
        for template_file in self.files:
            if template_file.is_template:
                # Logique de rendu simple (à améliorer avec Jinja2)
                content = template_file.content
                for key, value in params.items():
                    content = content.replace(f"{{{{{key}}}}}", str(value))
                rendered[template_file.path] = content
            else:
                rendered[template_file.path] = template_file.content
        return rendered


@dataclass
class CommandResult:
    """Résultat d'exécution de commande"""
    return_code: int
    stdout: str
    stderr: str
    execution_time: float
    success: bool
    error: Optional[Exception] = None


@dataclass
class ExportResult:
    """Résultat d'export"""
    success: bool
    message: str
    output_path: Path
    format: ExportFormat
    items_exported: int
    warnings: List[str] = field(default_factory=list)


@dataclass
class ActivationResult:
    """Résultat d'activation"""
    success: bool
    message: str
    activation_script: Path
    activation_command: str
    environment_variables: Dict[str, str] = field(default_factory=dict)


@dataclass
class RepairResult:
    """Résultat de réparation"""
    success: bool
    message: str
    issues_fixed: List[str] = field(default_factory=list)
    issues_remaining: List[str] = field(default_factory=list)
    actions_taken: List[str] = field(default_factory=list)


@dataclass
class CacheAddResult:
    """Résultat d'ajout au cache"""
    success: bool
    message: str
    package: str = ""
    version: str = ""
    file_size: int = 0
    cached_files: List[str] = field(default_factory=list)