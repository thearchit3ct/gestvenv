"""
GestVenv v1.1 - Modèles de Données
=================================

Module contenant les structures de données principales pour GestVenv.
Assure la compatibilité ascendante avec v1.0 tout en supportant les nouvelles
fonctionnalités v1.1 (pyproject.toml, backends multiples).

Classes principales:
    - EnvironmentInfo: Représentation complète d'un environnement virtuel
    - PackageInfo: Informations sur un package installé
    - PyProjectInfo: Métadonnées extraites d'un pyproject.toml
    - EnvironmentHealth: État de santé d'un environnement
    - ConfigInfo: Configuration globale de GestVenv

Version: 1.1.0
Auteur: thearchit3ct
Date: 2025-01-27
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
import json
import re

# Import conditionnel pour la validation
try:
    from packaging import version
    HAS_PACKAGING = True
except ImportError:
    HAS_PACKAGING = False


# ===== ENUMS ET CONSTANTES =====

class BackendType(Enum):
    """Types de backends supportés pour la gestion des packages."""
    PIP = "pip"
    UV = "uv"
    POETRY = "poetry"
    PDM = "pdm"
    CONDA = "conda"
    AUTO = "auto"  # Détection automatique


class SourceFileType(Enum):
    """Types de fichiers source supportés."""
    REQUIREMENTS = "requirements"  # requirements.txt
    PYPROJECT = "pyproject"       # pyproject.toml
    PIPFILE = "pipfile"          # Pipfile (Pipenv)
    CONDA_ENV = "conda_env"      # environment.yml


class HealthStatus(Enum):
    """États de santé d'un environnement."""
    HEALTHY = "healthy"
    WARNING = "warning"
    BROKEN = "broken"
    UNKNOWN = "unknown"


# Version du schéma pour la migration
SCHEMA_VERSION = "1.1.0"
COMPATIBLE_VERSIONS = ["1.0.0", "1.0.1", "1.1.0"]


# ===== CLASSES DE DONNÉES =====

@dataclass
class EnvironmentHealth:
    """État de santé et diagnostics d'un environnement virtuel."""
    status: HealthStatus = HealthStatus.UNKNOWN
    last_check: datetime = field(default_factory=datetime.now)
    python_path_valid: bool = True
    packages_consistent: bool = True
    dependencies_resolved: bool = True
    disk_usage_mb: Optional[int] = None
    issues: List[str] = field(default_factory=list)
    
    def is_healthy(self) -> bool:
        """Vérifie si l'environnement est en bonne santé."""
        return (
            self.status == HealthStatus.HEALTHY and
            self.python_path_valid and
            self.packages_consistent and
            self.dependencies_resolved
        )
    
    def add_issue(self, issue: str) -> None:
        """Ajoute un problème détecté."""
        if issue not in self.issues:
            self.issues.append(issue)
            if self.status == HealthStatus.HEALTHY:
                self.status = HealthStatus.WARNING


@dataclass
class PackageInfo:
    """Informations sur un package Python installé."""
    name: str
    version: str
    source: str = "unknown"
    is_editable: bool = False
    dependencies: List[str] = field(default_factory=list)
    backend_used: str = "pip"
    installed_at: datetime = field(default_factory=datetime.now)
    location: Optional[Path] = None
    requires_python: Optional[str] = None
    
    def __post_init__(self):
        """Validation et normalisation après initialisation."""
        self.name = self.name.lower()  # Normalisation nom package
        if isinstance(self.location, str):
            self.location = Path(self.location)
    
    def compare_version(self, other: str) -> int:
        """
        Compare avec une autre version.
        
        Returns:
            -1 si self.version < other
             0 si self.version == other  
             1 si self.version > other
        """
        if not HAS_PACKAGING:
            # Fallback simple si packaging non disponible
            return 0 if self.version == other else (1 if self.version > other else -1)
        
        try:
            v1 = version.parse(self.version)
            v2 = version.parse(other)
            return (v1 > v2) - (v1 < v2)
        except Exception:
            return 0
    
    def is_compatible(self, python_version: str) -> bool:
        """Vérifie la compatibilité avec une version Python."""
        if not self.requires_python or not HAS_PACKAGING:
            return True
        
        try:
            python_ver = version.parse(python_version)
            # Parsing basique des spécifications de version
            spec = self.requires_python.replace(" ", "")
            if ">=" in spec:
                min_ver = version.parse(spec.split(">=")[1].split(",")[0])
                return python_ver >= min_ver
            elif ">" in spec:
                min_ver = version.parse(spec.split(">")[1].split(",")[0])
                return python_ver > min_ver
            return True
        except Exception:
            return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Sérialise en dictionnaire."""
        result = asdict(self)
        if self.location:
            result['location'] = str(self.location)
        result['installed_at'] = self.installed_at.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PackageInfo':
        """Désérialise depuis un dictionnaire."""
        data = data.copy()
        if 'location' in data and data['location']:
            data['location'] = Path(data['location'])
        if 'installed_at' in data:
            data['installed_at'] = datetime.fromisoformat(data['installed_at'])
        return cls(**data)


@dataclass
class PyProjectInfo:
    """
    Informations extraites d'un fichier pyproject.toml.
    Conforme aux PEP 621 (métadonnées), PEP 517/518 (build system).
    """
    # === MÉTADONNÉES PROJET (PEP 621) ===
    name: str = ""
    version: str = "0.1.0"
    description: Optional[str] = None
    readme: Optional[str] = None
    requires_python: Optional[str] = None
    license: Optional[Dict[str, str]] = None
    authors: List[Dict[str, str]] = field(default_factory=list)
    maintainers: List[Dict[str, str]] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    classifiers: List[str] = field(default_factory=list)
    urls: Dict[str, str] = field(default_factory=dict)
    
    # === DÉPENDANCES ===
    dependencies: List[str] = field(default_factory=list)
    optional_dependencies: Dict[str, List[str]] = field(default_factory=dict)
    
    # === BUILD SYSTEM (PEP 517/518) ===
    build_system: Dict[str, Any] = field(default_factory=dict)
    
    # === SCRIPTS ET ENTRY POINTS ===
    scripts: Dict[str, str] = field(default_factory=dict)
    gui_scripts: Dict[str, str] = field(default_factory=dict)
    entry_points: Dict[str, Any] = field(default_factory=dict)
    
    # === SECTIONS OUTILS ===
    tool_sections: Dict[str, Any] = field(default_factory=dict)
    
    # === MÉTADONNÉES PARSING ===
    source_path: Optional[Path] = None
    last_modified: Optional[datetime] = None
    parsed_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validation et normalisation après initialisation."""
        if isinstance(self.source_path, str):
            self.source_path = Path(self.source_path)
    
    def validate_pep621(self) -> Tuple[bool, List[str]]:
        """
        Valide la conformité PEP 621.
        
        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_errors)
        """
        errors = []
        
        # Nom requis
        if not self.name or not isinstance(self.name, str):
            errors.append("Champ 'name' requis et doit être une chaîne")
        elif not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$', self.name):
            errors.append(f"Nom de projet invalide: {self.name}")
        
        # Version valide
        if self.version and HAS_PACKAGING:
            try:
                version.parse(self.version)
            except Exception:
                errors.append(f"Version invalide: {self.version}")
        
        # requires-python valide
        if self.requires_python:
            if not re.match(r'^[><=!]+\s*\d+(\.\d+)*', self.requires_python):
                errors.append(f"Spécification requires-python invalide: {self.requires_python}")
        
        # Authors format
        for author in self.authors:
            if not isinstance(author, dict) or ('name' not in author and 'email' not in author):
                errors.append("Auteur doit avoir au moins 'name' ou 'email'")
        
        return len(errors) == 0, errors
    
    def get_dependency_groups(self) -> List[str]:
        """Retourne la liste des groupes de dépendances optionnelles."""
        return list(self.optional_dependencies.keys())
    
    def extract_dependencies(self, groups: Optional[List[str]] = None) -> List[str]:
        """
        Extrait les dépendances pour les groupes spécifiés.
        
        Args:
            groups: Groupes optionnels à inclure. Si None, inclut seulement les dépendances principales.
        
        Returns:
            Liste des dépendances normalisées
        """
        deps = self.dependencies.copy()
        
        if groups:
            for group in groups:
                if group in self.optional_dependencies:
                    deps.extend(self.optional_dependencies[group])
        
        # Déduplique en préservant l'ordre
        seen = set()
        result = []
        for dep in deps:
            if dep not in seen:
                seen.add(dep)
                result.append(dep)
        
        return result
    
    def get_build_backend(self) -> str:
        """Retourne le backend de build spécifié ou un par défaut."""
        return self.build_system.get('build-backend', 'setuptools.build_meta')
    
    def get_build_requires(self) -> List[str]:
        """Retourne les dépendances de build."""
        return self.build_system.get('requires', ['setuptools', 'wheel'])
    
    def to_dict(self) -> Dict[str, Any]:
        """Sérialise en dictionnaire."""
        result = asdict(self)
        if self.source_path:
            result['source_path'] = str(self.source_path)
        if self.last_modified:
            result['last_modified'] = self.last_modified.isoformat()
        result['parsed_at'] = self.parsed_at.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PyProjectInfo':
        """Désérialise depuis un dictionnaire."""
        data = data.copy()
        if 'source_path' in data and data['source_path']:
            data['source_path'] = Path(data['source_path'])
        if 'last_modified' in data and data['last_modified']:
            data['last_modified'] = datetime.fromisoformat(data['last_modified'])
        if 'parsed_at' in data:
            data['parsed_at'] = datetime.fromisoformat(data['parsed_at'])
        return cls(**data)


@dataclass
class EnvironmentInfo:
    """
    Informations complètes sur un environnement virtuel.
    Compatible v1.0 avec extensions v1.1.
    """
    # === CHAMPS CORE v1.0 (compatibilité) ===
    name: str
    path: Path
    python_version: str
    created_at: datetime = field(default_factory=datetime.now)
    packages: List[str] = field(default_factory=list)  # Rétrocompatibilité v1.0
    packages_installed: List[PackageInfo] = field(default_factory=list)
    health: EnvironmentHealth = field(default_factory=EnvironmentHealth)
    active: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # === NOUVEAUX CHAMPS v1.1 ===
    pyproject_info: Optional[PyProjectInfo] = None
    backend_type: str = "pip"  # pip, uv, poetry, pdm, auto
    source_file_type: str = "requirements"  # requirements, pyproject
    lock_file_path: Optional[Path] = None
    dependency_groups: Dict[str, List[str]] = field(default_factory=dict)
    
    # === MÉTADONNÉES v1.1 ===
    updated_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    usage_count: int = 0
    aliases: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    # === MIGRATION ===
    migrated_from_version: Optional[str] = None
    _schema_version: str = SCHEMA_VERSION
    
    def __post_init__(self):
        """Validation et normalisation après initialisation."""
        if isinstance(self.path, str):
            self.path = Path(self.path)
        if isinstance(self.lock_file_path, str):
            self.lock_file_path = Path(self.lock_file_path)
        
        # Synchronisation packages/packages_installed pour compatibilité v1.0
        if self.packages and not self.packages_installed:
            self.packages_installed = [
                PackageInfo(name=pkg, version="unknown") 
                for pkg in self.packages
            ]
        elif self.packages_installed and not self.packages:
            self.packages = [pkg.name for pkg in self.packages_installed]
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Valide la cohérence des informations de l'environnement.
        
        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_errors)
        """
        errors = []
        
        # Validations de base
        if not self.name:
            errors.append("Nom d'environnement requis")
        
        if not self.path or not isinstance(self.path, Path):
            errors.append("Chemin d'environnement invalide")
        
        if not self.python_version:
            errors.append("Version Python requise")
        
        # Validation backend
        if self.backend_type not in [bt.value for bt in BackendType]:
            errors.append(f"Backend invalide: {self.backend_type}")
        
        # Validation source file type
        if self.source_file_type not in [sft.value for sft in SourceFileType]:
            errors.append(f"Type de fichier source invalide: {self.source_file_type}")
        
        # Validation pyproject_info si type pyproject
        if self.source_file_type == SourceFileType.PYPROJECT.value and self.pyproject_info:
            is_valid, pyproject_errors = self.pyproject_info.validate_pep621()
            if not is_valid:
                errors.extend([f"PyProject: {err}" for err in pyproject_errors])
        
        # Validation cohérence packages
        if len(self.packages) != len(set(self.packages)):
            errors.append("Doublons détectés dans la liste des packages")
        
        return len(errors) == 0, errors
    
    def mark_as_used(self) -> None:
        """Marque l'environnement comme utilisé (stats d'usage)."""
        self.last_used = datetime.now()
        self.usage_count += 1
        self.updated_at = datetime.now()
    
    def add_alias(self, alias: str) -> bool:
        """Ajoute un alias à l'environnement."""
        if alias not in self.aliases:
            self.aliases.append(alias)
            self.updated_at = datetime.now()
            return True
        return False
    
    def remove_alias(self, alias: str) -> bool:
        """Supprime un alias de l'environnement."""
        if alias in self.aliases:
            self.aliases.remove(alias)
            self.updated_at = datetime.now()
            return True
        return False
    
    def add_tag(self, tag: str) -> bool:
        """Ajoute un tag à l'environnement."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now()
            return True
        return False
    
    def get_package_by_name(self, name: str) -> Optional[PackageInfo]:
        """Trouve un package installé par son nom."""
        name_lower = name.lower()
        for pkg in self.packages_installed:
            if pkg.name.lower() == name_lower:
                return pkg
        return None
    
    def update_package_info(self, package_info: PackageInfo) -> None:
        """Met à jour les informations d'un package."""
        # Supprime l'ancienne version
        self.packages_installed = [
            pkg for pkg in self.packages_installed 
            if pkg.name.lower() != package_info.name.lower()
        ]
        # Ajoute la nouvelle version
        self.packages_installed.append(package_info)
        
        # Synchronise la liste simple pour compatibilité v1.0
        self.packages = [pkg.name for pkg in self.packages_installed]
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Sérialise en dictionnaire pour sauvegarde."""
        result = asdict(self)
        
        # Conversion des types complexes
        result['path'] = str(self.path)
        if self.lock_file_path:
            result['lock_file_path'] = str(self.lock_file_path)
        
        # Dates
        result['created_at'] = self.created_at.isoformat()
        result['updated_at'] = self.updated_at.isoformat()
        if self.last_used:
            result['last_used'] = self.last_used.isoformat()
        
        # Objets complexes
        if self.pyproject_info:
            result['pyproject_info'] = self.pyproject_info.to_dict()
        
        result['health'] = asdict(self.health)
        result['health']['last_check'] = self.health.last_check.isoformat()
        
        result['packages_installed'] = [pkg.to_dict() for pkg in self.packages_installed]
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnvironmentInfo':
        """Désérialise depuis un dictionnaire."""
        data = data.copy()
        
        # Conversion des chemins
        data['path'] = Path(data['path'])
        if 'lock_file_path' in data and data['lock_file_path']:
            data['lock_file_path'] = Path(data['lock_file_path'])
        
        # Conversion des dates
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data.get('updated_at', data['created_at']))
        if 'last_used' in data and data['last_used']:
            data['last_used'] = datetime.fromisoformat(data['last_used'])
        
        # Health object
        if 'health' in data:
            health_data = data['health']
            health_data['last_check'] = datetime.fromisoformat(health_data['last_check'])
            health_data['status'] = HealthStatus(health_data['status'])
            data['health'] = EnvironmentHealth(**health_data)
        
        # PyProject info
        if 'pyproject_info' in data and data['pyproject_info']:
            data['pyproject_info'] = PyProjectInfo.from_dict(data['pyproject_info'])
        
        # Packages installés
        if 'packages_installed' in data:
            data['packages_installed'] = [
                PackageInfo.from_dict(pkg_data) 
                for pkg_data in data['packages_installed']
            ]
        
        return cls(**data)
    
    def migrate_from_v1_0(self) -> None:
        """Migre depuis le format v1.0 vers v1.1."""
        if not self.migrated_from_version:
            self.migrated_from_version = "1.0.0"
            
        # Valeurs par défaut v1.1
        if not hasattr(self, 'backend_type') or not self.backend_type:
            self.backend_type = "pip"
        if not hasattr(self, 'source_file_type') or not self.source_file_type:
            self.source_file_type = "requirements"
        if not hasattr(self, 'updated_at'):
            self.updated_at = datetime.now()
        if not hasattr(self, 'usage_count'):
            self.usage_count = 0
        if not hasattr(self, 'aliases'):
            self.aliases = []
        if not hasattr(self, 'tags'):
            self.tags = []
        
        self._schema_version = SCHEMA_VERSION


@dataclass
class ConfigInfo:
    """Configuration globale de GestVenv."""
    # === CONFIGURATION DE BASE ===
    environments: Dict[str, EnvironmentInfo] = field(default_factory=dict)
    active_env: Optional[str] = None
    default_python: str = "python3"
    
    # === PARAMÈTRES v1.1 ===
    preferred_backend: str = "auto"  # auto, pip, uv, poetry, pdm
    auto_activate: bool = False
    use_package_cache: bool = True
    offline_mode: bool = False
    
    # === PARAMÈTRES BACKENDS ===
    backend_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # === ALIASES ET TEMPLATES ===
    global_aliases: Dict[str, str] = field(default_factory=dict)
    templates: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # === MÉTADONNÉES ===
    config_version: str = SCHEMA_VERSION
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    migrated_from_version: Optional[str] = None
    
    def get_environment(self, name: str) -> Optional[EnvironmentInfo]:
        """Récupère un environnement par nom ou alias."""
        # Recherche directe
        if name in self.environments:
            return self.environments[name]
        
        # Recherche par alias global
        if name in self.global_aliases:
            real_name = self.global_aliases[name]
            return self.environments.get(real_name)
        
        # Recherche par alias d'environnement
        for env in self.environments.values():
            if name in env.aliases:
                return env
        
        return None
    
    def add_environment(self, env_info: EnvironmentInfo) -> bool:
        """Ajoute un nouvel environnement."""
        if env_info.name in self.environments:
            return False
        
        self.environments[env_info.name] = env_info
        self.updated_at = datetime.now()
        return True
    
    def remove_environment(self, name: str) -> bool:
        """Supprime un environnement."""
        if name not in self.environments:
            return False
        
        # Désactive si c'était l'environnement actif
        if self.active_env == name:
            self.active_env = None
        
        # Supprime les alias globaux pointant vers cet environnement
        self.global_aliases = {
            alias: target for alias, target in self.global_aliases.items()
            if target != name
        }
        
        del self.environments[name]
        self.updated_at = datetime.now()
        return True
    
    def set_active_environment(self, name: str) -> bool:
        """Définit l'environnement actif."""
        env = self.get_environment(name)
        if not env:
            return False
        
        # Désactive l'ancien environnement
        if self.active_env:
            old_env = self.get_environment(self.active_env)
            if old_env:
                old_env.active = False
        
        # Active le nouvel environnement
        self.active_env = env.name
        env.active = True
        env.mark_as_used()
        
        self.updated_at = datetime.now()
        return True
    
    def migrate_from_v1_0(self) -> None:
        """Migre la configuration depuis v1.0."""
        if not self.migrated_from_version:
            self.migrated_from_version = "1.0.0"
        
        # Migre chaque environnement
        for env in self.environments.values():
            env.migrate_from_v1_0()
        
        # Paramètres par défaut v1.1
        if not hasattr(self, 'preferred_backend'):
            self.preferred_backend = "auto"
        if not hasattr(self, 'backend_configs'):
            self.backend_configs = {}
        if not hasattr(self, 'global_aliases'):
            self.global_aliases = {}
        if not hasattr(self, 'templates'):
            self.templates = {}
        
        self.config_version = SCHEMA_VERSION
        self.updated_at = datetime.now()


# ===== FONCTIONS UTILITAIRES =====

def create_default_pyproject_info(name: str, description: str = "") -> PyProjectInfo:
    """Crée une PyProjectInfo par défaut pour un nouveau projet."""
    return PyProjectInfo(
        name=name,
        version="0.1.0",
        description=description,
        build_system={
            "requires": ["setuptools>=45", "wheel"],
            "build-backend": "setuptools.build_meta"
        },
        tool_sections={}
    )


def create_environment_info(
    name: str,
    path: Path,
    python_version: str,
    backend_type: str = "pip",
    source_file_type: str = "requirements"
) -> EnvironmentInfo:
    """Crée une nouvelle EnvironmentInfo avec les paramètres de base."""
    return EnvironmentInfo(
        name=name,
        path=path,
        python_version=python_version,
        backend_type=backend_type,
        source_file_type=source_file_type,
        health=EnvironmentHealth(status=HealthStatus.UNKNOWN)
    )


def is_compatible_version(env_version: str) -> bool:
    """Vérifie si une version d'environnement est compatible."""
    return env_version in COMPATIBLE_VERSIONS


# ===== EXPORTS =====

__all__ = [
    # Enums
    'BackendType',
    'SourceFileType', 
    'HealthStatus',
    
    # Classes principales
    'EnvironmentInfo',
    'PackageInfo',
    'PyProjectInfo',
    'EnvironmentHealth',
    'ConfigInfo',
    
    # Utilitaires
    'create_default_pyproject_info',
    'create_environment_info',
    'is_compatible_version',
    
    # Constantes
    'SCHEMA_VERSION',
    'COMPATIBLE_VERSIONS'
]