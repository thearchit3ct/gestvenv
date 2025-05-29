"""
Module définissant les structures de données utilisées dans GestVenv v1.1.

Ce module contient des dataclasses représentant les différentes entités
manipulées par le gestionnaire d'environnements virtuels, avec support
étendu pour pyproject.toml et backends multiples.

Version 1.1 - Nouvelles fonctionnalités:
- Support pyproject.toml avec PyProjectInfo
- Backends multiples (pip, uv, poetry, pdm)
- Groupes de dépendances avancés
- Lock files et synchronisation
- Métadonnées étendues et migration
- Monitoring de performance et sécurité
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Set, Union
from enum import Enum
import re


class BackendType(Enum):
    """Types de backends supportés pour la gestion des packages."""
    PIP = "pip"
    UV = "uv"
    POETRY = "poetry"
    PDM = "pdm"
    CONDA = "conda"


class SourceFileType(Enum):
    """Types de fichiers sources pour les dépendances."""
    REQUIREMENTS = "requirements"
    PYPROJECT = "pyproject"
    POETRY_LOCK = "poetry_lock"
    PDM_LOCK = "pdm_lock"
    CONDA_ENV = "conda_env"


class DependencyType(Enum):
    """Types de dépendances dans un projet."""
    MAIN = "main"
    DEV = "dev"
    TEST = "test"
    DOCS = "docs"
    BUILD = "build"
    OPTIONAL = "optional"


@dataclass
class PackageInfo:
    """Classe représentant les informations d'un package Python."""
    name: str
    version: str
    required_by: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    
    # Nouveaux champs v1.1
    dependency_type: DependencyType = DependencyType.MAIN
    source: str = "pypi"  # pypi, git, local, url
    extras: List[str] = field(default_factory=list)
    markers: Optional[str] = None  # Environment markers
    hashes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet en dictionnaire pour la sérialisation."""
        return {
            "name": self.name,
            "version": self.version,
            "required_by": self.required_by,
            "dependencies": self.dependencies,
            "dependency_type": self.dependency_type.value,
            "source": self.source,
            "extras": self.extras,
            "markers": self.markers,
            "hashes": self.hashes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PackageInfo":
        """Crée une instance à partir d'un dictionnaire."""
        # Gestion compatibilité v1.0
        dependency_type = DependencyType.MAIN
        if "dependency_type" in data:
            try:
                dependency_type = DependencyType(data["dependency_type"])
            except ValueError:
                dependency_type = DependencyType.MAIN
        
        return cls(
            name=data["name"],
            version=data["version"],
            required_by=data.get("required_by", []),
            dependencies=data.get("dependencies", []),
            dependency_type=dependency_type,
            source=data.get("source", "pypi"),
            extras=data.get("extras", []),
            markers=data.get("markers"),
            hashes=data.get("hashes", [])
        )
    
    @property
    def full_name(self) -> str:
        """Retourne le nom complet du package avec sa version."""
        base = f"{self.name}=={self.version}"
        if self.extras:
            base = f"{self.name}[{','.join(self.extras)}]=={self.version}"
        if self.markers:
            base = f"{base}; {self.markers}"
        return base
    
    def to_requirement_string(self) -> str:
        """Convertit vers format requirement string."""
        return self.full_name


@dataclass
class EnvironmentHealth:
    """Classe représentant l'état de santé d'un environnement virtuel."""
    exists: bool = False
    python_available: bool = False
    pip_available: bool = False
    activation_script_exists: bool = False
    
    # Nouveaux champs v1.1
    backend_available: bool = False
    lock_file_valid: bool = True
    dependencies_synchronized: bool = True
    security_issues: List[str] = field(default_factory=list)
    performance_score: Optional[float] = None
    last_health_check: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet en dictionnaire pour la sérialisation."""
        return {
            "exists": self.exists,
            "python_available": self.python_available,
            "pip_available": self.pip_available,
            "activation_script_exists": self.activation_script_exists,
            "backend_available": self.backend_available,
            "lock_file_valid": self.lock_file_valid,
            "dependencies_synchronized": self.dependencies_synchronized,
            "security_issues": self.security_issues,
            "performance_score": self.performance_score,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnvironmentHealth":
        """Crée une instance à partir d'un dictionnaire."""
        last_health_check = None
        if data.get("last_health_check"):
            try:
                last_health_check = datetime.fromisoformat(data["last_health_check"])
            except (ValueError, TypeError):
                pass
        
        return cls(
            exists=data.get("exists", False),
            python_available=data.get("python_available", False),
            pip_available=data.get("pip_available", False),
            activation_script_exists=data.get("activation_script_exists", False),
            backend_available=data.get("backend_available", False),
            lock_file_valid=data.get("lock_file_valid", True),
            dependencies_synchronized=data.get("dependencies_synchronized", True),
            security_issues=data.get("security_issues", []),
            performance_score=data.get("performance_score"),
            last_health_check=last_health_check
        )
    
    @property
    def is_healthy(self) -> bool:
        """Vérifie si l'environnement est en bonne santé."""
        return (
            self.exists and 
            self.python_available and 
            self.pip_available and 
            self.activation_script_exists and
            self.lock_file_valid and
            len(self.security_issues) == 0
        )
    
    @property
    def health_score(self) -> float:
        """Calcule un score de santé global (0.0 - 1.0)."""
        checks = [
            self.exists,
            self.python_available,
            self.pip_available,
            self.activation_script_exists,
            self.backend_available,
            self.lock_file_valid,
            self.dependencies_synchronized,
            len(self.security_issues) == 0
        ]
        
        basic_score = sum(checks) / len(checks)
        
        # Bonus performance si disponible
        if self.performance_score is not None:
            return (basic_score * 0.8) + (self.performance_score * 0.2)
        
        return basic_score


@dataclass
class PyProjectInfo:
    """Informations extraites d'un fichier pyproject.toml."""
    
    # Build system (PEP 517/518)
    build_system: Dict[str, Any] = field(default_factory=dict)
    
    # Project metadata (PEP 621)
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
    
    # Dependencies
    dependencies: List[str] = field(default_factory=list)
    optional_dependencies: Dict[str, List[str]] = field(default_factory=dict)
    
    # URLs and entry points
    urls: Dict[str, str] = field(default_factory=dict)
    scripts: Dict[str, str] = field(default_factory=dict)
    gui_scripts: Dict[str, str] = field(default_factory=dict)
    entry_points: Dict[str, Dict[str, str]] = field(default_factory=dict)
    
    # Tool sections
    tool_sections: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    file_path: Optional[Path] = None
    last_modified: Optional[datetime] = None
    parsed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet en dictionnaire pour la sérialisation."""
        return {
            "build_system": self.build_system,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "readme": self.readme,
            "requires_python": self.requires_python,
            "license": self.license,
            "authors": self.authors,
            "maintainers": self.maintainers,
            "keywords": self.keywords,
            "classifiers": self.classifiers,
            "dependencies": self.dependencies,
            "optional_dependencies": self.optional_dependencies,
            "urls": self.urls,
            "scripts": self.scripts,
            "gui_scripts": self.gui_scripts,
            "entry_points": self.entry_points,
            "tool_sections": self.tool_sections,
            "file_path": str(self.file_path) if self.file_path else None,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
            "parsed_at": self.parsed_at.isoformat() if self.parsed_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PyProjectInfo":
        """Crée une instance à partir d'un dictionnaire."""
        # Conversion des dates
        last_modified = None
        parsed_at = None
        
        if data.get("last_modified"):
            try:
                last_modified = datetime.fromisoformat(data["last_modified"])
            except (ValueError, TypeError):
                pass
        
        if data.get("parsed_at"):
            try:
                parsed_at = datetime.fromisoformat(data["parsed_at"])
            except (ValueError, TypeError):
                pass
        
        file_path = None
        if data.get("file_path"):
            file_path = Path(data["file_path"])
        
        return cls(
            build_system=data.get("build_system", {}),
            name=data.get("name", ""),
            version=data.get("version", "0.1.0"),
            description=data.get("description"),
            readme=data.get("readme"),
            requires_python=data.get("requires_python"),
            license=data.get("license"),
            authors=data.get("authors", []),
            maintainers=data.get("maintainers", []),
            keywords=data.get("keywords", []),
            classifiers=data.get("classifiers", []),
            dependencies=data.get("dependencies", []),
            optional_dependencies=data.get("optional_dependencies", {}),
            urls=data.get("urls", {}),
            scripts=data.get("scripts", {}),
            gui_scripts=data.get("gui_scripts", {}),
            entry_points=data.get("entry_points", {}),
            tool_sections=data.get("tool_sections", {}),
            file_path=file_path,
            last_modified=last_modified,
            parsed_at=parsed_at
        )
    
    def get_dependency_groups(self) -> Dict[str, List[str]]:
        """Retourne tous les groupes de dépendances."""
        groups = {"main": self.dependencies.copy()}
        groups.update(self.optional_dependencies)
        return groups
    
    def get_all_dependencies(self, include_optional: bool = True) -> List[str]:
        """Retourne toutes les dépendances."""
        all_deps = self.dependencies.copy()
        if include_optional:
            for deps in self.optional_dependencies.values():
                all_deps.extend(deps)
        return list(set(all_deps))  # Supprime les doublons
    
    def has_build_backend(self) -> bool:
        """Vérifie si un build backend est configuré."""
        return bool(self.build_system.get("build-backend"))
    
    def get_build_backend(self) -> Optional[str]:
        """Retourne le build backend configuré."""
        return self.build_system.get("build-backend")


@dataclass
class LockFileInfo:
    """Informations sur un fichier de lock (uv.lock, poetry.lock, etc.)."""
    file_path: Path
    lock_type: str  # "uv", "poetry", "pdm", etc.
    created_at: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    python_version: Optional[str] = None
    packages_count: int = 0
    hash_algorithm: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet en dictionnaire pour la sérialisation."""
        return {
            "file_path": str(self.file_path),
            "lock_type": self.lock_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
            "python_version": self.python_version,
            "packages_count": self.packages_count,
            "hash_algorithm": self.hash_algorithm,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LockFileInfo":
        """Crée une instance à partir d'un dictionnaire."""
        created_at = None
        last_modified = None
        
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                pass
        
        if data.get("last_modified"):
            try:
                last_modified = datetime.fromisoformat(data["last_modified"])
            except (ValueError, TypeError):
                pass
        
        return cls(
            file_path=Path(data["file_path"]),
            lock_type=data["lock_type"],
            created_at=created_at,
            last_modified=last_modified,
            python_version=data.get("python_version"),
            packages_count=data.get("packages_count", 0),
            hash_algorithm=data.get("hash_algorithm"),
            metadata=data.get("metadata", {})
        )
    
    @property
    def is_outdated(self, reference_file: Optional[Path] = None) -> bool:
        """Vérifie si le lock file est obsolète."""
        if not reference_file or not self.last_modified:
            return False
        
        try:
            ref_modified = datetime.fromtimestamp(reference_file.stat().st_mtime)
            return ref_modified > self.last_modified
        except (OSError, TypeError):
            return True


@dataclass
class EnvironmentInfo:
    """Classe représentant les informations d'un environnement virtuel."""
    name: str
    path: Path
    python_version: str
    created_at: datetime = field(default_factory=datetime.now)
    packages: List[str] = field(default_factory=list)
    packages_installed: List[PackageInfo] = field(default_factory=list)
    health: EnvironmentHealth = field(default_factory=EnvironmentHealth)
    active: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Nouveaux champs v1.1
    pyproject_info: Optional[PyProjectInfo] = None
    backend_type: BackendType = BackendType.PIP
    source_file_type: SourceFileType = SourceFileType.REQUIREMENTS
    lock_file_info: Optional[LockFileInfo] = None
    dependency_groups: Dict[str, List[str]] = field(default_factory=dict)
    
    # Gestion avancée
    aliases: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    description: Optional[str] = None
    project_path: Optional[Path] = None
    
    # Statistiques et performance
    last_used: Optional[datetime] = None
    usage_count: int = 0
    average_install_time: Optional[float] = None
    cache_size: int = 0
    
    # Migration et compatibilité
    migrated_from_version: Optional[str] = None
    migration_notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet en dictionnaire pour la sérialisation."""
        return {
            # Champs v1.0 (compatibilité)
            "name": self.name,
            "path": str(self.path),
            "python_version": self.python_version,
            "created_at": self.created_at.isoformat(),
            "packages": self.packages,
            "packages_installed": [pkg.to_dict() for pkg in self.packages_installed],
            "health": self.health.to_dict(),
            "active": self.active,
            "metadata": self.metadata,
            
            # Nouveaux champs v1.1
            "pyproject_info": self.pyproject_info.to_dict() if self.pyproject_info else None,
            "backend_type": self.backend_type.value,
            "source_file_type": self.source_file_type.value,
            "lock_file_info": self.lock_file_info.to_dict() if self.lock_file_info else None,
            "dependency_groups": self.dependency_groups,
            "aliases": self.aliases,
            "tags": self.tags,
            "description": self.description,
            "project_path": str(self.project_path) if self.project_path else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "usage_count": self.usage_count,
            "average_install_time": self.average_install_time,
            "cache_size": self.cache_size,
            "migrated_from_version": self.migrated_from_version,
            "migration_notes": self.migration_notes,
            
            # Métadonnées version
            "_gestvenv_version": "1.1.0",
            "_schema_version": "1.1"
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnvironmentInfo":
        """Crée une instance à partir d'un dictionnaire."""
        # Conversion des dates
        if isinstance(data.get("created_at"), str):
            created_at = datetime.fromisoformat(data["created_at"])
        else:
            created_at = datetime.now()
        
        last_used = None
        if data.get("last_used"):
            try:
                last_used = datetime.fromisoformat(data["last_used"])
            except (ValueError, TypeError):
                pass
        
        # Conversion des packages installés (compatibilité v1.0)
        packages_installed = []
        for pkg_data in data.get("packages_installed", []):
            if isinstance(pkg_data, dict):
                packages_installed.append(PackageInfo.from_dict(pkg_data))
            elif isinstance(pkg_data, str):
                # Format v1.0 : "package==version"
                name, version = pkg_data.split("==") if "==" in pkg_data else (pkg_data, "")
                packages_installed.append(PackageInfo(name=name, version=version))
        
        # Conversion de l'état de santé
        health_data = data.get("health", {})
        if isinstance(health_data, dict):
            health = EnvironmentHealth.from_dict(health_data)
        else:
            health = EnvironmentHealth()
        
        # Conversion pyproject_info
        pyproject_info = None
        if data.get("pyproject_info"):
            pyproject_info = PyProjectInfo.from_dict(data["pyproject_info"])
        
        # Conversion lock file info
        lock_file_info = None
        if data.get("lock_file_info"):
            lock_file_info = LockFileInfo.from_dict(data["lock_file_info"])
        
        # Backend type (compatibilité v1.0)
        backend_type = BackendType.PIP
        if "backend_type" in data:
            try:
                backend_type = BackendType(data["backend_type"])
            except ValueError:
                backend_type = BackendType.PIP
        
        # Source file type (compatibilité v1.0)
        source_file_type = SourceFileType.REQUIREMENTS
        if "source_file_type" in data:
            try:
                source_file_type = SourceFileType(data["source_file_type"])
            except ValueError:
                source_file_type = SourceFileType.REQUIREMENTS
        
        return cls(
            name=data["name"],
            path=Path(data["path"]),
            python_version=data["python_version"],
            created_at=created_at,
            packages=data.get("packages", []),
            packages_installed=packages_installed,
            health=health,
            active=data.get("active", False),
            metadata=data.get("metadata", {}),
            pyproject_info=pyproject_info,
            backend_type=backend_type,
            source_file_type=source_file_type,
            lock_file_info=lock_file_info,
            dependency_groups=data.get("dependency_groups", {}),
            aliases=data.get("aliases", []),
            tags=data.get("tags", []),
            description=data.get("description"),
            project_path=Path(data["project_path"]) if data.get("project_path") else None,
            last_used=last_used,
            usage_count=data.get("usage_count", 0),
            average_install_time=data.get("average_install_time"),
            cache_size=data.get("cache_size", 0),
            migrated_from_version=data.get("migrated_from_version"),
            migration_notes=data.get("migration_notes", [])
        )
    
    @property
    def is_healthy(self) -> bool:
        """Vérifie si l'environnement est en bonne santé."""
        return self.health.is_healthy
    
    @property
    def has_pyproject(self) -> bool:
        """Vérifie si l'environnement a des informations pyproject.toml."""
        return self.pyproject_info is not None
    
    @property
    def has_lock_file(self) -> bool:
        """Vérifie si l'environnement a un fichier de lock."""
        return self.lock_file_info is not None
    
    def get_all_dependencies(self, include_dev: bool = True) -> List[str]:
        """Retourne toutes les dépendances de l'environnement."""
        if self.pyproject_info:
            return self.pyproject_info.get_all_dependencies(include_dev)
        return self.packages.copy()
    
    def get_dependencies_by_group(self, group: str) -> List[str]:
        """Retourne les dépendances d'un groupe spécifique."""
        if self.pyproject_info:
            groups = self.pyproject_info.get_dependency_groups()
            return groups.get(group, [])
        return self.dependency_groups.get(group, [])
    
    def update_usage_stats(self) -> None:
        """Met à jour les statistiques d'utilisation."""
        self.last_used = datetime.now()
        self.usage_count += 1
    
    def add_tag(self, tag: str) -> None:
        """Ajoute un tag à l'environnement."""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str) -> None:
        """Supprime un tag de l'environnement."""
        if tag in self.tags:
            self.tags.remove(tag)
    
    def add_alias(self, alias: str) -> None:
        """Ajoute un alias à l'environnement."""
        if alias not in self.aliases:
            self.aliases.append(alias)
    
    def remove_alias(self, alias: str) -> None:
        """Supprime un alias de l'environnement."""
        if alias in self.aliases:
            self.aliases.remove(alias)


@dataclass
class ConfigInfo:
    """Classe représentant la configuration globale de GestVenv."""
    environments: Dict[str, EnvironmentInfo] = field(default_factory=dict)
    active_env: Optional[str] = None
    default_python: str = "python3"
    settings: Dict[str, Any] = field(default_factory=dict)
    
    # Nouveaux champs v1.1
    preferred_backend: BackendType = BackendType.PIP
    backend_settings: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    global_aliases: Dict[str, str] = field(default_factory=dict)
    templates: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Migration et version
    config_version: str = "1.1.0"
    migrated_from_version: Optional[str] = None
    migration_date: Optional[datetime] = None
    
    def __post_init__(self) -> None:
        """Initialise les valeurs par défaut pour les paramètres."""
        if not self.settings:
            self.settings = {
                # Paramètres v1.0 (compatibilité)
                "auto_activate": True,
                "package_cache_enabled": True,
                "check_updates_on_activate": True,
                "default_export_format": "json",
                "show_virtual_env_in_prompt": True,
                
                # Nouveaux paramètres v1.1
                "preferred_backend": "auto",
                "pyproject_support": True,
                "show_migration_hints": True,
                "auto_detect_project_type": True,
                "performance_monitoring": True,
                "security_scanning": True,
                "cache_optimization": True,
                
                # Paramètres avancés
                "parallel_installs": True,
                "max_parallel_jobs": 4,
                "install_timeout": 300,
                "health_check_interval": 86400,  # 24h en secondes
                "auto_cleanup_orphaned": True,
                "backup_on_migration": True
            }
        
        # Initialisation des paramètres backend par défaut
        if not self.backend_settings:
            self.backend_settings = {
                "pip": {
                    "index_url": None,
                    "extra_index_urls": [],
                    "trusted_hosts": [],
                    "timeout": 60,
                    "retries": 3
                },
                "uv": {
                    "python_preference": "managed",
                    "resolution": "highest",
                    "prerelease": "disallow",
                    "compile_bytecode": True
                },
                "poetry": {
                    "virtualenvs_create": True,
                    "virtualenvs_in_project": False
                }
            }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet en dictionnaire pour la sérialisation."""
        return {
            "environments": {name: env.to_dict() for name, env in self.environments.items()},
            "active_env": self.active_env,
            "default_python": self.default_python,
            "settings": self.settings,
            "preferred_backend": self.preferred_backend.value,
            "backend_settings": self.backend_settings,
            "global_aliases": self.global_aliases,
            "templates": self.templates,
            "config_version": self.config_version,
            "migrated_from_version": self.migrated_from_version,
            "migration_date": self.migration_date.isoformat() if self.migration_date else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConfigInfo":
        """Crée une instance à partir d'un dictionnaire."""
        environments = {}
        env_data = data.get("environments", {})
        
        for name, env_dict in env_data.items():
            if isinstance(env_dict, dict):
                env_dict["name"] = name  # Assurer que le nom est inclus
                environments[name] = EnvironmentInfo.from_dict(env_dict)
        
        # Backend type (compatibilité v1.0)
        preferred_backend = BackendType.PIP
        if "preferred_backend" in data:
            try:
                if data["preferred_backend"] == "auto":
                    preferred_backend = BackendType.PIP  # Default pour auto
                else:
                    preferred_backend = BackendType(data["preferred_backend"])
            except ValueError:
                preferred_backend = BackendType.PIP
        
        # Migration date
        migration_date = None
        if data.get("migration_date"):
            try:
                migration_date = datetime.fromisoformat(data["migration_date"])
            except (ValueError, TypeError):
                pass
        
        return cls(
            environments=environments,
            active_env=data.get("active_env"),
            default_python=data.get("default_python", "python3"),
            settings=data.get("settings", {}),
            preferred_backend=preferred_backend,
            backend_settings=data.get("backend_settings", {}),
            global_aliases=data.get("global_aliases", {}),
            templates=data.get("templates", {}),
            config_version=data.get("config_version", "1.1.0"),
            migrated_from_version=data.get("migrated_from_version"),
            migration_date=migration_date
        )
    
    def get_environment_by_alias(self, alias: str) -> Optional[EnvironmentInfo]:
        """Récupère un environnement par son alias."""
        # Chercher dans les alias globaux
        if alias in self.global_aliases:
            env_name = self.global_aliases[alias]
            return self.environments.get(env_name)
        
        # Chercher dans les alias locaux des environnements
        for env in self.environments.values():
            if alias in env.aliases:
                return env
        
        return None
    
    def add_global_alias(self, alias: str, env_name: str) -> bool:
        """Ajoute un alias global."""
        if env_name in self.environments:
            self.global_aliases[alias] = env_name
            return True
        return False
    
    def remove_global_alias(self, alias: str) -> bool:
        """Supprime un alias global."""
        if alias in self.global_aliases:
            del self.global_aliases[alias]
            return True
        return False
    
    def get_backend_setting(self, backend: Union[str, BackendType], setting: str, default: Any = None) -> Any:
        """Récupère un paramètre spécifique à un backend."""
        backend_name = backend.value if isinstance(backend, BackendType) else backend
        return self.backend_settings.get(backend_name, {}).get(setting, default)
    
    def set_backend_setting(self, backend: Union[str, BackendType], setting: str, value: Any) -> None:
        """Définit un paramètre spécifique à un backend."""
        backend_name = backend.value if isinstance(backend, BackendType) else backend
        if backend_name not in self.backend_settings:
            self.backend_settings[backend_name] = {}
        self.backend_settings[backend_name][setting] = value
    
    def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Récupère un template de configuration."""
        return self.templates.get(template_name)
    
    def add_template(self, template_name: str, template_data: Dict[str, Any]) -> None:
        """Ajoute un template de configuration."""
        self.templates[template_name] = template_data
    
    def list_environments_by_backend(self, backend: BackendType) -> List[EnvironmentInfo]:
        """Liste les environnements utilisant un backend spécifique."""
        return [env for env in self.environments.values() if env.backend_type == backend]
    
    def list_environments_by_tag(self, tag: str) -> List[EnvironmentInfo]:
        """Liste les environnements ayant un tag spécifique."""
        return [env for env in self.environments.values() if tag in env.tags]
    
    def get_environment_stats(self) -> Dict[str, Any]:
        """Retourne des statistiques sur les environnements."""
        total_envs = len(self.environments)
        active_envs = sum(1 for env in self.environments.values() if env.active)
        healthy_envs = sum(1 for env in self.environments.values() if env.is_healthy)
        
        backend_counts = {}
        for env in self.environments.values():
            backend = env.backend_type.value
            backend_counts[backend] = backend_counts.get(backend, 0) + 1
        
        source_counts = {}
        for env in self.environments.values():
            source = env.source_file_type.value
            source_counts[source] = source_counts.get(source, 0) + 1
        
        return {
            "total_environments": total_envs,
            "active_environments": active_envs,
            "healthy_environments": healthy_envs,
            "health_percentage": (healthy_envs / total_envs * 100) if total_envs > 0 else 0,
            "backend_distribution": backend_counts,
            "source_type_distribution": source_counts,
            "total_packages": sum(len(env.packages_installed) for env in self.environments.values()),
            "average_packages_per_env": sum(len(env.packages_installed) for env in self.environments.values()) / total_envs if total_envs > 0 else 0
        }


@dataclass
class ValidationError:
    """Classe représentant une erreur de validation."""
    field: str
    message: str
    severity: str = "error"  # "error", "warning", "info"
    code: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'erreur en dictionnaire."""
        return {
            "field": self.field,
            "message": self.message,
            "severity": self.severity,
            "code": self.code,
            "context": self.context
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationError":
        """Crée une instance depuis un dictionnaire."""
        return cls(
            field=data["field"],
            message=data["message"],
            severity=data.get("severity", "error"),
            code=data.get("code"),
            context=data.get("context", {})
        )


@dataclass
class MigrationInfo:
    """Informations sur une migration d'environnement."""
    from_version: str
    to_version: str
    migration_type: str  # "config", "environment", "backend"
    started_at: datetime
    completed_at: Optional[datetime] = None
    success: bool = False
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    backup_path: Optional[Path] = None
    rollback_available: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet en dictionnaire pour la sérialisation."""
        return {
            "from_version": self.from_version,
            "to_version": self.to_version,
            "migration_type": self.migration_type,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "success": self.success,
            "errors": [error.to_dict() for error in self.errors],
            "warnings": [warning.to_dict() for warning in self.warnings],
            "backup_path": str(self.backup_path) if self.backup_path else None,
            "rollback_available": self.rollback_available,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MigrationInfo":
        """Crée une instance à partir d'un dictionnaire."""
        started_at = datetime.fromisoformat(data["started_at"])
        completed_at = None
        if data.get("completed_at"):
            completed_at = datetime.fromisoformat(data["completed_at"])
        
        errors = [ValidationError.from_dict(err) for err in data.get("errors", [])]
        warnings = [ValidationError.from_dict(warn) for warn in data.get("warnings", [])]
        
        backup_path = None
        if data.get("backup_path"):
            backup_path = Path(data["backup_path"])
        
        return cls(
            from_version=data["from_version"],
            to_version=data["to_version"],
            migration_type=data["migration_type"],
            started_at=started_at,
            completed_at=completed_at,
            success=data.get("success", False),
            errors=errors,
            warnings=warnings,
            backup_path=backup_path,
            rollback_available=data.get("rollback_available", False),
            metadata=data.get("metadata", {})
        )
    
    @property
    def duration(self) -> Optional[float]:
        """Retourne la durée de la migration en secondes."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def has_errors(self) -> bool:
        """Vérifie si la migration a des erreurs."""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Vérifie si la migration a des avertissements."""
        return len(self.warnings) > 0


@dataclass
class SecurityIssue:
    """Représente un problème de sécurité détecté."""
    package_name: str
    vulnerability_id: str
    severity: str  # "low", "medium", "high", "critical"
    description: str
    affected_versions: List[str] = field(default_factory=list)
    fixed_versions: List[str] = field(default_factory=list)
    cve_id: Optional[str] = None
    discovered_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet en dictionnaire pour la sérialisation."""
        return {
            "package_name": self.package_name,
            "vulnerability_id": self.vulnerability_id,
            "severity": self.severity,
            "description": self.description,
            "affected_versions": self.affected_versions,
            "fixed_versions": self.fixed_versions,
            "cve_id": self.cve_id,
            "discovered_at": self.discovered_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SecurityIssue":
        """Crée une instance à partir d'un dictionnaire."""
        discovered_at = datetime.now()
        if data.get("discovered_at"):
            try:
                discovered_at = datetime.fromisoformat(data["discovered_at"])
            except (ValueError, TypeError):
                pass
        
        return cls(
            package_name=data["package_name"],
            vulnerability_id=data["vulnerability_id"],
            severity=data["severity"],
            description=data["description"],
            affected_versions=data.get("affected_versions", []),
            fixed_versions=data.get("fixed_versions", []),
            cve_id=data.get("cve_id"),
            discovered_at=discovered_at,
            metadata=data.get("metadata", {})
        )
    
    @property
    def severity_score(self) -> int:
        """Retourne un score numérique pour la gravité."""
        severity_scores = {
            "low": 1,
            "medium": 2,
            "high": 3,
            "critical": 4
        }
        return severity_scores.get(self.severity, 0)


@dataclass
class PerformanceMetrics:
    """Métriques de performance pour un environnement."""
    environment_name: str
    backend_type: str
    measurement_type: str  # "install", "update", "sync", "create"
    duration: float  # en secondes
    package_count: int
    success: bool
    measured_at: datetime = field(default_factory=datetime.now)
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    disk_io: Optional[float] = None
    network_io: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet en dictionnaire pour la sérialisation."""
        return {
            "environment_name": self.environment_name,
            "backend_type": self.backend_type,
            "measurement_type": self.measurement_type,
            "duration": self.duration,
            "package_count": self.package_count,
            "success": self.success,
            "measured_at": self.measured_at.isoformat(),
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "disk_io": self.disk_io,
            "network_io": self.network_io,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PerformanceMetrics":
        """Crée une instance à partir d'un dictionnaire."""
        measured_at = datetime.now()
        if data.get("measured_at"):
            try:
                measured_at = datetime.fromisoformat(data["measured_at"])
            except (ValueError, TypeError):
                pass
        
        return cls(
            environment_name=data["environment_name"],
            backend_type=data["backend_type"],
            measurement_type=data["measurement_type"],
            duration=data["duration"],
            package_count=data["package_count"],
            success=data["success"],
            measured_at=measured_at,
            cpu_usage=data.get("cpu_usage"),
            memory_usage=data.get("memory_usage"),
            disk_io=data.get("disk_io"),
            network_io=data.get("network_io"),
            metadata=data.get("metadata", {})
        )
    
    @property
    def packages_per_second(self) -> float:
        """Calcule le nombre de packages traités par seconde."""
        if self.duration > 0:
            return self.package_count / self.duration
        return 0.0
    
    @property
    def efficiency_score(self) -> float:
        """Calcule un score d'efficacité (0.0 - 1.0)."""
        if not self.success:
            return 0.0
        
        base_score = min(1.0, self.packages_per_second / 10.0)  # Normalise sur 10 packages/sec
        
        # Pénalité pour usage CPU/mémoire élevé
        if self.cpu_usage and self.cpu_usage > 80:
            base_score *= 0.8
        if self.memory_usage and self.memory_usage > 1000:  # > 1GB
            base_score *= 0.9
        
        return base_score


# Fonctions utilitaires pour les modèles

def create_default_environment_info(name: str, path: Path, python_version: str) -> EnvironmentInfo:
    """Crée un EnvironmentInfo avec des valeurs par défaut."""
    return EnvironmentInfo(
        name=name,
        path=path,
        python_version=python_version,
        created_at=datetime.now(),
        health=EnvironmentHealth(),
        backend_type=BackendType.PIP,
        source_file_type=SourceFileType.REQUIREMENTS
    )


def create_default_config_info() -> ConfigInfo:
    """Crée un ConfigInfo avec des valeurs par défaut."""
    return ConfigInfo(
        environments={},
        active_env=None,
        default_python="python3",
        preferred_backend=BackendType.PIP
    )


def validate_environment_name(name: str) -> List[ValidationError]:
    """Valide un nom d'environnement."""
    errors = []
    
    if not name:
        errors.append(ValidationError("name", "Le nom ne peut pas être vide"))
    
    if len(name) > 50:
        errors.append(ValidationError("name", "Le nom est trop long (maximum 50 caractères)"))
    
    if not name.replace("-", "").replace("_", "").isalnum():
        errors.append(ValidationError("name", "Le nom ne peut contenir que des lettres, chiffres, tirets et underscores"))
    
    reserved_names = ["system", "admin", "config", "test", "tmp", "temp"]
    if name.lower() in reserved_names:
        errors.append(ValidationError("name", f"'{name}' est un nom réservé"))
    
    return errors


def validate_python_version(version: str) -> List[ValidationError]:
    """Valide une version Python."""
    errors = []
    
    if not version:
        return errors  # Version vide est acceptable (utilise la version par défaut)
    
    valid_patterns = [
        r'^python,
        r'^python3,
        r'^python3\.\d+,
        r'^3\.\d+,
        r'^py,
        r'^py -3\.\d+
    ]
    
    if not any(re.match(pattern, version) for pattern in valid_patterns):
        errors.append(ValidationError("python_version", f"Format de version Python invalide: {version}"))
    
    # Vérifier version minimale
    match: Any = re.match(r'^3\.(\d+), version)
    if match:
        minor = int(match.group(1))
        if minor < 9:
            errors.append(ValidationError("python_version", "GestVenv nécessite Python 3.9 ou supérieur"))
    
    return errors


def get_model_version() -> str:
    """Retourne la version du schéma des modèles."""
    return "1.1.0"


def is_compatible_version(version: str) -> bool:
    """Vérifie si une version de schéma est compatible."""
    compatible_versions = ["1.0.0", "1.1.0"]
    return version in compatible_versions


# Export des classes et fonctions principales
__all__ = [
    # Enums
    "BackendType",
    "SourceFileType", 
    "DependencyType",
    
    # Classes principales
    "PackageInfo",
    "EnvironmentHealth",
    "PyProjectInfo",
    "LockFileInfo",
    "EnvironmentInfo",
    "ConfigInfo",
    
    # Classes utilitaires
    "ValidationError",
    "MigrationInfo",
    "SecurityIssue",
    "PerformanceMetrics",
    
    # Fonctions utilitaires
    "create_default_environment_info",
    "create_default_config_info",
    "validate_environment_name",
    "validate_python_version",
    "get_model_version",
    "is_compatible_version"
] # type: ignore