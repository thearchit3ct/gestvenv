"""
Tests unitaires pour ConfigManager
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, mock_open, Mock

from gestvenv.core.config_manager import ConfigManager
from gestvenv.core.models import Config
from gestvenv.core.exceptions import ConfigurationError, ValidationError


class TestConfigManager:
    """Tests pour ConfigManager"""
    
    @pytest.fixture
    def temp_dir(self):
        """Répertoire temporaire pour tests"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def config_path(self, temp_dir):
        """Chemin fichier config test"""
        return temp_dir / "config.json"

    def test_init_sans_chemin(self):
        """Test initialisation sans chemin spécifique"""
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path("/home/user")
            
            manager = ConfigManager()
            
            expected_path = Path("/home/user/.gestvenv/config.json")
            assert manager.config_path == expected_path

    def test_init_avec_chemin(self, config_path):
        """Test initialisation avec chemin spécifique"""
        manager = ConfigManager(config_path)
        
        assert manager.config_path == config_path

    def test_load_config_fichier_inexistant(self, config_path):
        """Test chargement config fichier inexistant"""
        manager = ConfigManager(config_path)
        
        # Devrait créer config par défaut
        assert isinstance(manager.config, Config)
        assert manager.config.version == "1.1.0"

    def test_load_config_fichier_existant_valide(self, config_path):
        """Test chargement config fichier valide"""
        config_data = {
            "version": "1.1.0",
            "default_python_version": "3.10",
            "cache_enabled": False,
            "auto_migrate": False
        }
        
        config_path.write_text(json.dumps(config_data))
        manager = ConfigManager(config_path)
        
        assert manager.config.default_python_version == "3.10"
        assert manager.config.cache_enabled is False
        assert manager.config.auto_migrate is False

    def test_load_config_fichier_json_invalide(self, config_path):
        """Test chargement config JSON invalide"""
        config_path.write_text("{ invalid json }")
        
        with pytest.raises(ConfigurationError):
            ConfigManager(config_path)

    def test_load_config_donnees_invalides(self, config_path):
        """Test chargement données invalides"""
        config_data = {
            "version": "1.1.0",
            "default_python_version": "invalid_version",
            "cache_ttl_hours": -1
        }
        
        config_path.write_text(json.dumps(config_data))
        
        with pytest.raises(ConfigurationError):
            ConfigManager(config_path)

    def test_save_config_nouveau_fichier(self, config_path):
        """Test sauvegarde nouveau fichier"""
        manager = ConfigManager(config_path)
        manager.config.default_python_version = "3.10"
        
        manager.save_config()
        
        # Vérification fichier créé
        assert config_path.exists()
        
        # Vérification contenu
        data = json.loads(config_path.read_text())
        assert data["default_python_version"] == "3.10"

    def test_save_config_ecrase_fichier(self, config_path):
        """Test sauvegarde écrase fichier existant"""
        # Création fichier initial
        initial_data = {"version": "1.0.0"}
        config_path.write_text(json.dumps(initial_data))
        
        manager = ConfigManager(config_path)
        manager.save_config()
        
        # Vérification écrasement
        data = json.loads(config_path.read_text())
        assert data["version"] == "1.1.0"

    def test_save_config_erreur_ecriture(self, config_path):
        """Test erreur sauvegarde"""
        manager = ConfigManager(config_path)
        
        # Simulation erreur écriture
        with patch('pathlib.Path.write_text', side_effect=OSError("Permission denied")):
            with pytest.raises(ConfigurationError):
                manager.save_config()

    def test_update_config_valeurs_valides(self, config_path):
        """Test mise à jour config valeurs valides"""
        manager = ConfigManager(config_path)
        
        updates = {
            "default_python_version": "3.10",
            "cache_enabled": False,
            "max_parallel_jobs": 2
        }
        
        manager.update_config(updates)
        
        assert manager.config.default_python_version == "3.10"
        assert manager.config.cache_enabled is False
        assert manager.config.max_parallel_jobs == 2

    def test_update_config_valeurs_invalides(self, config_path):
        """Test mise à jour config valeurs invalides"""
        manager = ConfigManager(config_path)
        
        updates = {
            "default_python_version": "invalid",
            "cache_ttl_hours": -1
        }
        
        with pytest.raises(ValidationError):
            manager.update_config(updates)

    def test_update_config_cles_inexistantes(self, config_path):
        """Test mise à jour clés inexistantes"""
        manager = ConfigManager(config_path)
        
        updates = {
            "unknown_setting": "value"
        }
        
        # Devrait ignorer les clés inconnues
        manager.update_config(updates)
        
        assert not hasattr(manager.config, "unknown_setting")

    def test_reset_config(self, config_path):
        """Test remise à zéro config"""
        manager = ConfigManager(config_path)
        manager.config.default_python_version = "3.10"
        manager.config.cache_enabled = False
        
        manager.reset_config()
        
        # Vérification valeurs par défaut restaurées
        assert manager.config.default_python_version == "3.11"
        assert manager.config.cache_enabled is True

    def test_get_setting_existant(self, config_path):
        """Test récupération setting existant"""
        manager = ConfigManager(config_path)
        
        value = manager.get_setting("default_python_version")
        
        assert value == "3.11"

    def test_get_setting_inexistant(self, config_path):
        """Test récupération setting inexistant"""
        manager = ConfigManager(config_path)
        
        value = manager.get_setting("unknown_setting")
        
        assert value is None

    def test_get_setting_avec_defaut(self, config_path):
        """Test récupération setting avec valeur par défaut"""
        manager = ConfigManager(config_path)
        
        value = manager.get_setting("unknown_setting", "default_value")
        
        assert value == "default_value"

    def test_set_setting_valide(self, config_path):
        """Test définition setting valide"""
        manager = ConfigManager(config_path)
        
        manager.set_setting("default_python_version", "3.10")
        
        assert manager.config.default_python_version == "3.10"

    def test_set_setting_invalide(self, config_path):
        """Test définition setting invalide"""
        manager = ConfigManager(config_path)
        
        with pytest.raises(ValidationError):
            manager.set_setting("default_python_version", "invalid")

    def test_set_setting_inexistant(self, config_path):
        """Test définition setting inexistant"""
        manager = ConfigManager(config_path)
        
        # Devrait ignorer silencieusement
        manager.set_setting("unknown_setting", "value")
        
        assert not hasattr(manager.config, "unknown_setting")

    def test_backup_config(self, config_path):
        """Test sauvegarde config"""
        manager = ConfigManager(config_path)
        manager.save_config()  # Créer fichier initial
        
        backup_path = manager.backup_config()
        
        assert backup_path.exists()
        assert backup_path.suffix == ".backup"
        
        # Vérification contenu identique
        original_data = json.loads(config_path.read_text())
        backup_data = json.loads(backup_path.read_text())
        assert original_data == backup_data

    def test_backup_config_fichier_inexistant(self, config_path):
        """Test sauvegarde config fichier inexistant"""
        manager = ConfigManager(config_path)
        
        backup_path = manager.backup_config()
        
        assert backup_path is None

    def test_restore_config_valide(self, config_path):
        """Test restauration config valide"""
        manager = ConfigManager(config_path)
        
        # Créer backup
        backup_data = {
            "version": "1.1.0",
            "default_python_version": "3.9"
        }
        backup_path = config_path.with_suffix(".backup")
        backup_path.write_text(json.dumps(backup_data))
        
        success = manager.restore_config(backup_path)
        
        assert success is True
        assert manager.config.default_python_version == "3.9"

    def test_restore_config_invalide(self, config_path):
        """Test restauration config invalide"""
        manager = ConfigManager(config_path)
        
        # Backup invalide
        backup_path = config_path.with_suffix(".backup")
        backup_path.write_text("{ invalid json }")
        
        success = manager.restore_config(backup_path)
        
        assert success is False

    def test_validate_config_valide(self, config_path):
        """Test validation config valide"""
        manager = ConfigManager(config_path)
        
        assert manager.validate_config() is True

    def test_validate_config_invalide(self, config_path):
        """Test validation config invalide"""
        manager = ConfigManager(config_path)
        manager.config.default_python_version = "invalid"
        
        assert manager.validate_config() is False

    def test_get_environments_path(self, config_path):
        """Test récupération chemin environnements"""
        manager = ConfigManager(config_path)
        
        path = manager.get_environments_path()
        
        assert isinstance(path, Path)
        assert path.name == "environments"

    def test_get_cache_path(self, config_path):
        """Test récupération chemin cache"""
        manager = ConfigManager(config_path)
        
        path = manager.get_cache_path()
        
        assert isinstance(path, Path)
        assert path.name == "cache"

    def test_ensure_directories_creation(self, config_path):
        """Test création répertoires nécessaires"""
        manager = ConfigManager(config_path)
        
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            manager.ensure_directories()
            
            # Vérification création répertoires
            assert mock_mkdir.call_count >= 2  # config dir + environments + cache

    def test_ensure_directories_deja_existants(self, config_path):
        """Test répertoires déjà existants"""
        manager = ConfigManager(config_path)
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.mkdir') as mock_mkdir:
                manager.ensure_directories()
                
                # Ne devrait pas tenter de créer
                mock_mkdir.assert_not_called()

    def test_migration_config_v1_0(self, config_path):
        """Test migration config v1.0"""
        # Config v1.0
        old_config = {
            "python_version": "3.10",  # Ancien nom
            "use_cache": True,         # Ancien nom
            "environments_dir": "/old/path"
        }
        
        config_path.write_text(json.dumps(old_config))
        manager = ConfigManager(config_path)
        
        # Vérification migration
        assert manager.config.default_python_version == "3.10"
        assert manager.config.cache_enabled is True

    def test_thread_safety_config(self, config_path):
        """Test sécurité thread config"""
        import threading
        import time
        
        manager = ConfigManager(config_path)
        results = []
        
        def update_config(value):
            manager.set_setting("default_python_version", f"3.{value}")
            results.append(manager.get_setting("default_python_version"))
        
        # Lancement threads concurrents
        threads = []
        for i in range(5):
            thread = threading.Thread(target=update_config, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Vérification cohérence
        assert len(results) == 5
        assert all(result.startswith("3.") for result in results)