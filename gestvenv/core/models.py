"""
Module définissant les structures de données utilisées dans GestVenv.

Ce module contient des dataclasses représentant les différentes entités
manipulées par le gestionnaire d'environnements virtuels.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Set, Union


@dataclass
class PackageInfo:
    """Classe représentant les informations d'un package Python."""
    name: str
    version: str
    required_by: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet en dictionnaire pour la sérialisation."""
        return {
            "name": self.name,
            "version": self.version,
            "required_by": self.required_by,
            "dependencies": self.dependencies
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PackageInfo":
        """Crée une instance à partir d'un dictionnaire."""
        return cls(
            name=data["name"],
            version=data["version"],
            required_by=data.get("required_by", []),
            dependencies=data.get("dependencies", [])
        )
    
    @property
    def full_name(self) -> str:
        """Retourne le nom complet du package avec sa version."""
        return f"{self.name}=={self.version}"


@dataclass
class EnvironmentHealth:
    """État de santé d'un environnement virtuel."""
    exists: bool = False
    python_available: bool = False
    pip_available: bool = False
    activation_script_exists: bool = False
    
    def to_dict(self) -> Dict[str, bool]:
        """Convertit l'objet en dictionnaire."""
        return {
            "exists": self.exists,
            "python_available": self.python_available,
            "pip_available": self.pip_available,
            "activation_script_exists": self.activation_script_exists
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, bool]) -> "EnvironmentHealth":
        """Crée une instance à partir d'un dictionnaire."""
        return cls(
            exists=data.get("exists", False),
            python_available=data.get("python_available", False),
            pip_available=data.get("pip_available", False),
            activation_script_exists=data.get("activation_script_exists", False)
        )


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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet en dictionnaire pour la sérialisation."""
        return {
            "name": self.name,
            "path": str(self.path),
            "python_version": self.python_version,
            "created_at": self.created_at.isoformat(),
            "packages": self.packages,
            "packages_installed": [pkg.to_dict() for pkg in self.packages_installed],
            "health": self.health.to_dict(),
            "active": self.active,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnvironmentInfo":
        """Crée une instance à partir d'un dictionnaire."""
        # Conversion des dates
        if isinstance(data.get("created_at"), str):
            created_at = datetime.fromisoformat(data["created_at"])
        else:
            created_at = datetime.now()
        
        # Conversion des packages installés
        packages_installed = []
        for pkg_data in data.get("packages_installed", []):
            if isinstance(pkg_data, dict):
                packages_installed.append(PackageInfo.from_dict(pkg_data))
            elif isinstance(pkg_data, str):
                # Ancien format - conversion simple
                name, version = pkg_data.split("==") if "==" in pkg_data else (pkg_data, "")
                packages_installed.append(PackageInfo(name=name, version=version))
        
        # Conversion de l'état de santé
        health_data = data.get("health", {})
        if isinstance(health_data, dict):
            health = EnvironmentHealth.from_dict(health_data)
        else:
            health = EnvironmentHealth()
        
        return cls(
            name=data["name"],
            path=Path(data["path"]),
            python_version=data["python_version"],
            created_at=created_at,
            packages=data.get("packages", []),
            packages_installed=packages_installed,
            health=health,
            active=data.get("active", False),
            metadata=data.get("metadata", {})
        )
    
    @property
    def is_healthy(self) -> bool:
        """Vérifie si l'environnement est en bonne santé."""
        return (self.health.exists and 
                self.health.python_available and 
                self.health.pip_available and 
                self.health.activation_script_exists)


@dataclass
class ConfigInfo:
    """Classe représentant la configuration globale de GestVenv."""
    environments: Dict[str, EnvironmentInfo] = field(default_factory=dict)
    active_env: Optional[str] = None
    default_python: str = "python3"
    settings: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Initialise les valeurs par défaut pour les paramètres."""
        if not self.settings:
            self.settings = {
                "auto_activate": True,
                "package_cache_enabled": True,
                "check_updates_on_activate": True,
                "default_export_format": "json",
                "show_virtual_env_in_prompt": True
            }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet en dictionnaire pour la sérialisation."""
        return {
            "environments": {name: env.to_dict() for name, env in self.environments.items()},
            "active_env": self.active_env,
            "default_python": self.default_python,
            "settings": self.settings
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
        
        return cls(
            environments=environments,
            active_env=data.get("active_env"),
            default_python=data.get("default_python", "python3"),
            settings=data.get("settings", {})
        )