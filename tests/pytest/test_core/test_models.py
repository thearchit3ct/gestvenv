"""Tests pour les classes de modèles du module core."""

from typing import Any, Dict
import pytest
from datetime import datetime
from pathlib import Path

from gestvenv.core.models import (
    PackageInfo, EnvironmentHealth, EnvironmentInfo, ConfigInfo
)

class TestPackageInfo:
    """Tests pour la classe PackageInfo."""
    
    def test_init(self) -> None:
        """Teste l'initialisation de la classe."""
        pkg = PackageInfo(name="flask", version="2.0.1")
        
        assert pkg.name == "flask"
        assert pkg.version == "2.0.1"
        assert pkg.required_by == []
        assert pkg.dependencies == []
    
    def test_to_dict(self) -> None:
        """Teste la conversion en dictionnaire."""
        pkg = PackageInfo(
            name="flask", 
            version="2.0.1", 
            required_by=["app"], 
            dependencies=["click", "werkzeug"]
        )
        
        pkg_dict = pkg.to_dict()
        
        assert pkg_dict["name"] == "flask"
        assert pkg_dict["version"] == "2.0.1"
        assert pkg_dict["required_by"] == ["app"]
        assert pkg_dict["dependencies"] == ["click", "werkzeug"]
    
    def test_from_dict(self) -> None:
        """Teste la création depuis un dictionnaire."""
        pkg_dict = {
            "name": "flask",
            "version": "2.0.1",
            "required_by": ["app"],
            "dependencies": ["click", "werkzeug"]
        }
        
        pkg = PackageInfo.from_dict(pkg_dict)
        
        assert pkg.name == "flask"
        assert pkg.version == "2.0.1"
        assert pkg.required_by == ["app"]
        assert pkg.dependencies == ["click", "werkzeug"]
    
    def test_full_name(self) -> None:
        """Teste la propriété full_name."""
        pkg = PackageInfo(name="flask", version="2.0.1")
        assert pkg.full_name == "flask==2.0.1"

class TestEnvironmentHealth:
    """Tests pour la classe EnvironmentHealth."""
    
    def test_init(self) -> None:
        """Teste l'initialisation de la classe."""
        health = EnvironmentHealth()
        
        assert health.exists is False
        assert health.python_available is False
        assert health.pip_available is False
        assert health.activation_script_exists is False
        
        health = EnvironmentHealth(
            exists=True,
            python_available=True,
            pip_available=True,
            activation_script_exists=True
        )
        
        assert health.exists is True
        assert health.python_available is True
        assert health.pip_available is True
        assert health.activation_script_exists is True
    
    def test_to_dict(self) -> None:
        """Teste la conversion en dictionnaire."""
        health = EnvironmentHealth(
            exists=True,
            python_available=True,
            pip_available=False,
            activation_script_exists=True
        )
        
        health_dict = health.to_dict()
        
        assert health_dict["exists"] is True
        assert health_dict["python_available"] is True
        assert health_dict["pip_available"] is False
        assert health_dict["activation_script_exists"] is True
    
    def test_from_dict(self) -> None:
        """Teste la création depuis un dictionnaire."""
        health_dict = {
            "exists": True,
            "python_available": True,
            "pip_available": False,
            "activation_script_exists": True
        }
        
        health = EnvironmentHealth.from_dict(health_dict)
        
        assert health.exists is True
        assert health.python_available is True
        assert health.pip_available is False
        assert health.activation_script_exists is True

class TestEnvironmentInfo:
    """Tests pour la classe EnvironmentInfo."""
    
    def test_init(self) -> None:
        """Teste l'initialisation de la classe."""
        env = EnvironmentInfo(
            name="test_env",
            path=Path("/path/to/test_env"),
            python_version="3.9.0"
        )
        
        assert env.name == "test_env"
        assert env.path == Path("/path/to/test_env")
        assert env.python_version == "3.9.0"
        assert isinstance(env.created_at, datetime)
        assert env.packages == []
        assert env.packages_installed == []
        assert isinstance(env.health, EnvironmentHealth)
        assert env.active is False
        assert env.metadata == {}
    
    def test_to_dict(self) -> None:
        """Teste la conversion en dictionnaire."""
        created_at = datetime(2023, 1, 1, 12, 0, 0)
        
        env = EnvironmentInfo(
            name="test_env",
            path=Path("/path/to/test_env"),
            python_version="3.9.0",
            created_at=created_at,
            packages=["flask", "pytest"],
            packages_installed=[
                PackageInfo(name="flask", version="2.0.1"),
                PackageInfo(name="pytest", version="6.2.5")
            ],
            health=EnvironmentHealth(exists=True, python_available=True),
            active=True,
            metadata={"description": "Test environment"}
        )
        
        env_dict = env.to_dict()
        
        assert env_dict["name"] == "test_env"
        assert env_dict["path"] == "/path/to/test_env"
        assert env_dict["python_version"] == "3.9.0"
        assert env_dict["created_at"] == created_at.isoformat()
        assert env_dict["packages"] == ["flask", "pytest"]
        assert len(env_dict["packages_installed"]) == 2
        assert env_dict["packages_installed"][0]["name"] == "flask"
        assert env_dict["health"]["exists"] is True
        assert env_dict["active"] is True
        assert env_dict["metadata"]["description"] == "Test environment"
    
    def test_from_dict(self) -> None:
        """Teste la création depuis un dictionnaire."""
        created_at = datetime(2023, 1, 1, 12, 0, 0)
        
        env_dict = {
            "name": "test_env",
            "path": "/path/to/test_env",
            "python_version": "3.9.0",
            "created_at": created_at.isoformat(),
            "packages": ["flask", "pytest"],
            "packages_installed": [
                {"name": "flask", "version": "2.0.1"},
                {"name": "pytest", "version": "6.2.5"}
            ],
            "health": {
                "exists": True,
                "python_available": True,
                "pip_available": False,
                "activation_script_exists": False
            },
            "active": True,
            "metadata": {"description": "Test environment"}
        }
        
        env = EnvironmentInfo.from_dict(env_dict)
        
        assert env.name == "test_env"
        assert env.path == Path("/path/to/test_env")
        assert env.python_version == "3.9.0"
        assert env.created_at.isoformat() == created_at.isoformat()
        assert env.packages == ["flask", "pytest"]
        assert len(env.packages_installed) == 2
        assert env.packages_installed[0].name == "flask"
        assert env.health.exists is True
        assert env.health.python_available is True
        assert env.active is True
        assert env.metadata["description"] == "Test environment"
    
    def test_is_healthy(self) -> None:
        """Teste la propriété is_healthy."""
        # Environnement en bonne santé
        env = EnvironmentInfo(
            name="test_env",
            path=Path("/path/to/test_env"),
            python_version="3.9.0",
            health=EnvironmentHealth(
                exists=True,
                python_available=True,
                pip_available=True,
                activation_script_exists=True
            )
        )
        
        assert env.is_healthy is True
        
        # Environnement avec problèmes
        env.health.pip_available = False
        assert env.is_healthy is False
        
        env.health.exists = False
        assert env.is_healthy is False

class TestConfigInfo:
    """Tests pour la classe ConfigInfo."""
    
    def test_init(self) -> None:
        """Teste l'initialisation de la classe."""
        config = ConfigInfo()
        
        assert config.environments == {}
        assert config.active_env is None
        assert config.default_python == "python3"
        assert "auto_activate" in config.settings
        
        # Test avec des valeurs personnalisées
        created_at = datetime(2023, 1, 1, 12, 0, 0)
        env = EnvironmentInfo(
            name="test_env",
            path=Path("/path/to/test_env"),
            python_version="3.9.0",
            created_at=created_at
        )
        
        config = ConfigInfo(
            environments={"test_env": env},
            active_env="test_env",
            default_python="python3.9",
            settings={
                "auto_activate": False,
                "custom_setting": "value"
            }
        )
        
        assert "test_env" in config.environments
        assert config.active_env == "test_env"
        assert config.default_python == "python3.9"
        assert config.settings["auto_activate"] is False
        assert config.settings["custom_setting"] == "value"
    
    def test_to_dict(self) -> None:
        """Teste la conversion en dictionnaire."""
        created_at = datetime(2023, 1, 1, 12, 0, 0)
        env = EnvironmentInfo(
            name="test_env",
            path=Path("/path/to/test_env"),
            python_version="3.9.0",
            created_at=created_at
        )
        
        config = ConfigInfo(
            environments={"test_env": env},
            active_env="test_env",
            default_python="python3.9",
            settings={
                "auto_activate": False,
                "custom_setting": "value"
            }
        )
        
        config_dict: Dict[str, Any] = config.to_dict()
        
        assert "environments" in config_dict
        assert "test_env" in config_dict["environments"]
        assert config_dict["active_env"] == "test_env"
        assert config_dict["default_python"] == "python3.9"
        assert config_dict["settings"]["auto_activate"] is False
        assert config_dict["settings"]["custom_setting"] == "value"
    
    def test_from_dict(self) -> None:
        """Teste la création depuis un dictionnaire."""
        created_at = datetime(2023, 1, 1, 12, 0, 0)
        
        config_dict = {
            "environments": {
                "test_env": {
                    "name": "test_env",
                    "path": "/path/to/test_env",
                    "python_version": "3.9.0",
                    "created_at": created_at.isoformat()
                }
            },
            "active_env": "test_env",
            "default_python": "python3.9",
            "settings": {
                "auto_activate": False,
                "custom_setting": "value"
            }
        }
        
        config = ConfigInfo.from_dict(config_dict)
        
        assert "test_env" in config.environments
        assert config.environments["test_env"].name == "test_env"
        assert config.environments["test_env"].python_version == "3.9.0"
        assert config.active_env == "test_env"
        assert config.default_python == "python3.9"
        assert config.settings["auto_activate"] is False
        assert config.settings["custom_setting"] == "value"