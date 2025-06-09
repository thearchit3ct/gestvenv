"""Tests pour la classe ConfigManager."""

import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Any
from pytest import MonkeyPatch
from datetime import datetime

from gestvenv.core.config_manager import ConfigManager
from gestvenv.core.models import EnvironmentInfo

class TestConfigManager:
    """Tests pour la classe ConfigManager."""
    
    @pytest.fixture
    def config_manager(self, temp_dir: Path) -> ConfigManager:
        """Crée un gestionnaire de configuration pour les tests."""
        config_file = temp_dir / "test_config.json"
        config_data = {
            "environments": {
                "test_env": {
                    "path": str(temp_dir / "environments" / "test_env"),
                    "python_version": "3.9.0",
                    "created_at": datetime.now().isoformat()
                }
            },
            "active_env": "test_env",  # Définir explicitement l'environnement actif
            "default_python": "python3",
            "settings": {
                "auto_activate": True,
                "package_cache_enabled": True,
                "check_updates_on_activate": True,
                "default_export_format": "json",
                "show_virtual_env_in_prompt": True,
                "version": "1.2.0"
            }
        }
    
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        return ConfigManager(config_path=config_file)
    
    def test_init(self, temp_dir: Path) -> None:
        """Teste l'initialisation de la classe."""
        # Avec un chemin de configuration spécifié
        config_path = temp_dir / "custom_config.json"
        manager = ConfigManager(config_path=config_path)
        
        assert manager.config_path == config_path
        assert manager.config is not None
        
        # Sans chemin spécifié (utilise le chemin par défaut)
        with patch('gestvenv.core.config_manager.ConfigManager._get_default_config_path') as mock_path:
            mock_path.return_value = temp_dir / "default_config.json"
            
            manager = ConfigManager()
            
            assert manager.config_path == temp_dir / "default_config.json"
            assert manager.config is not None
    
    # def test_get_default_config_path(self, monkeypatch: MonkeyPatch, temp_dir: Path) -> None:
    #     """Teste la récupération du chemin de configuration par défaut."""
    #     # Simuler différents systèmes d'exploitation
    #     with patch('os.name', 'nt'):  # Windows
    #         monkeypatch.setenv('APPDATA', str(temp_dir))
            
    #         path = ConfigManager._get_default_config_path(ConfigManager)
            
    #         assert "GestVenv" in str(path)
    #         assert "config.json" in str(path)
        
    #     with patch('os.name', 'posix'):  # Unix
    #         monkeypatch.setattr(Path, 'home', lambda: temp_dir)
            
    #         path = ConfigManager._get_default_config_path(ConfigManager)
            
    #         assert ".config" in str(path)
    #         assert "gestvenv" in str(path)
    #         assert "config.json" in str(path)
    
    def test_load_config(self, temp_dir: Path) -> None:
        """Teste le chargement de la configuration."""
        # Créer une configuration valide
        config_file = temp_dir / "valid_config.json"
        config_data = {
            "environments": {
                "test_env": {
                    "path": str(temp_dir / "environments" / "test_env"),
                    "python_version": "3.9.0",
                    "created_at": datetime.now().isoformat()
                }
            },
            "active_env": "test_env",
            "default_python": "python3",
        "settings": {
            "auto_activate": True,
            "package_cache_enabled": True,
            "check_updates_on_activate": True,
            "default_export_format": "json",
            "show_virtual_env_in_prompt": True,
            "version": "1.2.0"
        }
    }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Charger la configuration
        manager = ConfigManager(config_path=config_file)
        
        assert "test_env" in manager.config.environments
        assert manager.config.active_env == "test_env"
        assert manager.config.default_python == "python3"
        
        # Configuration invalide (JSON corrompu)
        invalid_file = temp_dir / "invalid_config.json"
        with open(invalid_file, 'w') as f:
            f.write("Invalid JSON")
        
        # Le gestionnaire devrait créer une configuration par défaut
        with patch('gestvenv.core.config_manager.ConfigManager._create_default_config') as mock_create:
            mock_create.return_value = {
                "environments": {},
                "active_env": None,
                "default_python": "python3",
        "settings": {
            "auto_activate": True,
            "package_cache_enabled": True,
            "check_updates_on_activate": True,
            "default_export_format": "json",
            "show_virtual_env_in_prompt": True,
            "version": "1.2.0"
        }
    }
            
            manager = ConfigManager(config_path=invalid_file)
            
            mock_create.assert_called_once()
        
        # Fichier de configuration inexistant
        nonexistent_file = temp_dir / "nonexistent_config.json"
        
        # Le gestionnaire devrait créer une configuration par défaut
        with patch('gestvenv.core.config_manager.ConfigManager._create_default_config') as mock_create:
            mock_create.return_value = {
                "environments": {},
                "active_env": None,
                "default_python": "python3",
        "settings": {
            "auto_activate": True,
            "package_cache_enabled": True,
            "check_updates_on_activate": True,
            "default_export_format": "json",
            "show_virtual_env_in_prompt": True,
            "version": "1.2.0"
        }
    }
            
            manager = ConfigManager(config_path=nonexistent_file)
            
            mock_create.assert_called_once()
    
    def test_save_config(self, config_manager: ConfigManager, temp_dir: Path) -> None:
        """Teste la sauvegarde de la configuration."""
        # Modifier la configuration
        config_manager.config.default_python = "python3.9"
        
        # Sauvegarder
        result = config_manager.save_config()
        
        # Vérifier le résultat
        assert result is True
        
        # Vérifier que le fichier a été créé
        assert config_manager.config_path.exists()
        
        # Vérifier le contenu
        with open(config_manager.config_path, 'r') as f:
            saved_config = json.load(f)
        
        assert saved_config["default_python"] == "python3.9"
        
        # Simuler une erreur d'écriture
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            result = config_manager.save_config()
            assert result is False
    
    def test_get_environment(self, config_manager: ConfigManager) -> None:
        """Teste la récupération d'un environnement spécifique."""
        # Environnement existant
        env = config_manager.get_environment("test_env")
        
        assert env is not None
        assert env.name == "test_env"
        assert env.python_version == "3.9.0"
        
        # Environnement inexistant
        env = config_manager.get_environment("nonexistent")
        assert env is None
    
    def test_get_all_environments(self, config_manager: ConfigManager) -> None:
        """Teste la récupération de tous les environnements."""
        envs = config_manager.get_all_environments()
        
        assert len(envs) == 1
        assert "test_env" in envs
    
    def test_add_environment(self, config_manager: ConfigManager, temp_dir: Path) -> None:
        """Teste l'ajout d'un nouvel environnement."""
        # Créer un nouvel environnement
        env = EnvironmentInfo(
            name="new_env",
            path=temp_dir / "environments" / "new_env",
            python_version="3.10.0"
        )
        
        # Ajouter l'environnement
        result = config_manager.add_environment(env)
        
        # Vérifier le résultat
        assert result is True
        assert "new_env" in config_manager.config.environments
        
        # Essayer d'ajouter un environnement existant
        result = config_manager.add_environment(env)
        assert result is False
    
    def test_update_environment(self, config_manager: ConfigManager) -> None:
        """Teste la mise à jour d'un environnement existant."""
        # Récupérer l'environnement existant
        env = config_manager.get_environment("test_env")
        
        # Modifier l'environnement
        env.python_version = "3.10.0"
        
        # Mettre à jour l'environnement
        result = config_manager.update_environment(env)
        
        # Vérifier le résultat
        assert result is True
        assert config_manager.config.environments["test_env"].python_version == "3.10.0"
        
        # Essayer de mettre à jour un environnement inexistant
        nonexistent_env = EnvironmentInfo(
            name="nonexistent",
            path=Path("/path/to/nonexistent"),
            python_version="3.9.0"
        )
        
        with pytest.raises(ValueError):
            config_manager.update_environment(nonexistent_env)
    
    def test_remove_environment(self, config_manager: ConfigManager) -> None:
        """Teste la suppression d'un environnement."""
        # Supprimer un environnement existant
        result = config_manager.remove_environment("test_env")
        
        # Vérifier le résultat
        assert result is True
        assert "test_env" not in config_manager.config.environments
        assert config_manager.config.active_env is None
        
        # Essayer de supprimer un environnement inexistant
        with pytest.raises(ValueError):
            config_manager.remove_environment("nonexistent")
    
    def test_environment_exists(self, config_manager: ConfigManager) -> None:
        """Teste la vérification de l'existence d'un environnement."""
        # Environnement existant
        assert config_manager.environment_exists("test_env") is True
        
        # Environnement inexistant
        assert config_manager.environment_exists("nonexistent") is False
    
    def test_get_active_environment(self, config_manager: ConfigManager) -> None:
        """Teste la récupération de l'environnement actif."""
        # L'environnement actif est défini dans le fichier de configuration
        assert config_manager.get_active_environment() == "test_env"
        
        # Réinitialiser l'environnement actif
        config_manager.config.active_env = None
        assert config_manager.get_active_environment() is None
    
    def test_set_active_environment(self, config_manager: ConfigManager) -> None:
        """Teste la définition de l'environnement actif."""
        # Définir un environnement existant comme actif
        result = config_manager.set_active_environment("test_env")
        
        # Vérifier le résultat
        assert result is True
        assert config_manager.config.active_env == "test_env"
        assert config_manager.config.environments["test_env"].active is True
        
        # Essayer de définir un environnement inexistant comme actif
        with pytest.raises(ValueError):
            config_manager.set_active_environment("nonexistent")
    
    def test_clear_active_environment(self, config_manager: ConfigManager) -> None:
        """Teste la réinitialisation de l'environnement actif."""
        # Réinitialiser l'environnement actif
        result = config_manager.clear_active_environment()
        
        # Vérifier le résultat
        assert result is True
        assert config_manager.config.active_env is None
        assert config_manager.config.environments["test_env"].active is False
    
    def test_get_set_default_python(self, config_manager: ConfigManager) -> None:
        """Teste la récupération et la définition de la commande Python par défaut."""
        # Récupérer la commande par défaut
        assert config_manager.get_default_python() == "python3"
        
        # Définir une nouvelle commande par défaut
        result = config_manager.set_default_python("python3.9")
        
        # Vérifier le résultat
        assert result is True
        assert config_manager.get_default_python() == "python3.9"