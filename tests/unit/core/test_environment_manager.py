"""
Tests unitaires pour EnvironmentManager
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import tempfile
import shutil

from gestvenv.core.environment_manager import EnvironmentManager
from gestvenv.core.config_manager import ConfigManager
from gestvenv.core.models import (
    EnvironmentInfo,
    EnvironmentResult,
    ActivationResult,
    SyncResult,
    ExportResult,
    DiagnosticReport,
    PyProjectInfo,
    BackendType,
    SourceFileType,
    ExportFormat,
    EnvironmentHealth
)
from gestvenv.core.exceptions import (
    EnvironmentNotFoundError,
    EnvironmentExistsError,
    ValidationError
)


class TestEnvironmentManager:
    """Tests pour EnvironmentManager"""
    
    @pytest.fixture
    def temp_dir(self):
        """Répertoire temporaire pour tests"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_config_manager(self):
        """ConfigManager mocké"""
        config_manager = Mock(spec=ConfigManager)
        config_manager.config = Mock()
        config_manager.config.environments_path = Path("/test/envs")
        config_manager.config.default_python_version = "3.11"
        config_manager.config.auto_migrate = True
        return config_manager

    @pytest.fixture
    def env_manager(self, mock_config_manager):
        """EnvironmentManager avec config mockée"""
        return EnvironmentManager(mock_config_manager)

    def test_init_sans_config(self):
        """Test initialisation sans ConfigManager"""
        with patch('gestvenv.core.environment_manager.ConfigManager') as mock_cm:
            manager = EnvironmentManager()
            mock_cm.assert_called_once()
            assert manager.config_manager is not None

    def test_init_avec_config(self, mock_config_manager):
        """Test initialisation avec ConfigManager"""
        manager = EnvironmentManager(mock_config_manager)
        assert manager.config_manager == mock_config_manager

    @patch('gestvenv.core.environment_manager.EnvironmentManager._validate_environment_name')
    @patch('gestvenv.core.environment_manager.EnvironmentManager._environment_exists')
    def test_create_environment_basique(self, mock_exists, mock_validate, env_manager):
        """Test création environnement basique"""
        mock_exists.return_value = False
        mock_validate.return_value = None
        
        # Mock backend manager
        env_manager._backend_manager = Mock()
        env_manager._backend_manager.get_preferred_backend.return_value = Mock()
        env_manager._backend_manager.get_preferred_backend.return_value.name = "uv"
        
        # Mock création environnement
        with patch.object(env_manager, '_create_virtual_environment') as mock_create:
            mock_create.return_value = EnvironmentResult(
                success=True,
                message="Environnement créé",
                environment=EnvironmentInfo("test_env", Path("/test/envs/test_env"), "3.11")
            )
            
            result = env_manager.create_environment("test_env", python_version="3.11")
            
            assert result.success is True
            assert result.environment.name == "test_env"
            mock_validate.assert_called_once_with("test_env")
            mock_exists.assert_called_once_with("test_env")

    def test_create_environment_existe_deja(self, env_manager):
        """Test création environnement existant"""
        with patch.object(env_manager, '_validate_environment_name'):
            with patch.object(env_manager, '_environment_exists', return_value=True):
                result = env_manager.create_environment("existing_env")
                
                assert result.success is False
                assert "existe déjà" in result.message

    def test_create_environment_nom_invalide(self, env_manager):
        """Test création avec nom invalide"""
        with patch.object(env_manager, '_validate_environment_name', 
                         side_effect=ValidationError("Nom invalide")):
            result = env_manager.create_environment("../invalid")
            
            assert result.success is False
            assert "Nom invalide" in result.message

    @patch('gestvenv.core.environment_manager.Path.exists')
    def test_create_from_pyproject_fichier_inexistant(self, mock_exists, env_manager):
        """Test création depuis pyproject.toml inexistant"""
        mock_exists.return_value = False
        
        result = env_manager.create_from_pyproject(
            pyproject_path=Path("/inexistant.toml"),
            env_name="test"
        )
        
        assert result.success is False
        assert "introuvable" in result.message

    @patch('gestvenv.core.environment_manager.Path.exists')
    def test_create_from_pyproject_valide(self, mock_exists, env_manager):
        """Test création depuis pyproject.toml valide"""
        mock_exists.return_value = True
        
        # Mock parser
        with patch.object(env_manager, '_parse_pyproject_file') as mock_parse:
            pyproject_info = PyProjectInfo(
                name="test-project",
                dependencies=["requests>=2.25.0"]
            )
            mock_parse.return_value = pyproject_info
            
            # Mock création environnement
            with patch.object(env_manager, 'create_environment') as mock_create:
                mock_env = EnvironmentInfo("test", Path("/test"), "3.11")
                mock_create.return_value = EnvironmentResult(
                    success=True,
                    environment=mock_env
                )
                
                result = env_manager.create_from_pyproject(
                    pyproject_path=Path("/test.toml"),
                    env_name="test"
                )
                
                assert result.success is True
                mock_parse.assert_called_once()
                mock_create.assert_called_once()

    def test_activate_environment_inexistant(self, env_manager):
        """Test activation environnement inexistant"""
        with patch.object(env_manager, 'get_environment_info', return_value=None):
            result = env_manager.activate_environment("inexistant")
            
            assert result.success is False
            assert "introuvable" in result.message

    def test_activate_environment_valide(self, env_manager):
        """Test activation environnement valide"""
        mock_env = EnvironmentInfo("test", Path("/test/envs/test"), "3.11")
        
        with patch.object(env_manager, 'get_environment_info', return_value=mock_env):
            with patch.object(env_manager, '_activate_environment_shell') as mock_activate:
                mock_activate.return_value = True
                
                result = env_manager.activate_environment("test")
                
                assert result.success is True
                mock_activate.assert_called_once_with(mock_env)

    def test_deactivate_environment(self, env_manager):
        """Test désactivation environnement"""
        with patch.object(env_manager, '_deactivate_current_environment') as mock_deactivate:
            mock_deactivate.return_value = True
            
            result = env_manager.deactivate_environment()
            
            assert result is True
            mock_deactivate.assert_called_once()

    def test_delete_environment_inexistant(self, env_manager):
        """Test suppression environnement inexistant"""
        with patch.object(env_manager, 'get_environment_info', return_value=None):
            result = env_manager.delete_environment("inexistant")
            
            assert result is False

    def test_delete_environment_valide(self, env_manager):
        """Test suppression environnement valide"""
        mock_env = EnvironmentInfo("test", Path("/test/envs/test"), "3.11")
        
        with patch.object(env_manager, 'get_environment_info', return_value=mock_env):
            with patch('shutil.rmtree') as mock_rmtree:
                with patch.object(env_manager, '_remove_environment_metadata') as mock_remove_meta:
                    result = env_manager.delete_environment("test")
                    
                    assert result is True
                    mock_rmtree.assert_called_once_with(mock_env.path)
                    mock_remove_meta.assert_called_once_with("test")

    def test_delete_environment_force(self, env_manager):
        """Test suppression forcée"""
        mock_env = EnvironmentInfo("test", Path("/test/envs/test"), "3.11")
        mock_env.is_active = True
        
        with patch.object(env_manager, 'get_environment_info', return_value=mock_env):
            with patch('shutil.rmtree'):
                with patch.object(env_manager, '_remove_environment_metadata'):
                    result = env_manager.delete_environment("test", force=True)
                    
                    assert result is True

    def test_list_environments_vide(self, env_manager):
        """Test liste environnements vide"""
        with patch.object(env_manager, '_load_all_environments', return_value=[]):
            envs = env_manager.list_environments()
            
            assert len(envs) == 0

    def test_list_environments_avec_filtres(self, env_manager):
        """Test liste avec filtres"""
        mock_envs = [
            EnvironmentInfo("env1", Path("/test/env1"), "3.11", health=EnvironmentHealth.HEALTHY),
            EnvironmentInfo("env2", Path("/test/env2"), "3.10", health=EnvironmentHealth.HAS_ERRORS),
            EnvironmentInfo("env3", Path("/test/env3"), "3.11", health=EnvironmentHealth.HEALTHY)
        ]
        
        with patch.object(env_manager, '_load_all_environments', return_value=mock_envs):
            # Filtre par version Python
            envs_311 = env_manager.list_environments(python_version="3.11")
            assert len(envs_311) == 2
            
            # Filtre par santé
            envs_healthy = env_manager.list_environments(health=EnvironmentHealth.HEALTHY)
            assert len(envs_healthy) == 2

    def test_sync_environment_inexistant(self, env_manager):
        """Test sync environnement inexistant"""
        with patch.object(env_manager, 'get_environment_info', return_value=None):
            result = env_manager.sync_environment("inexistant")
            
            assert result.success is False

    def test_sync_environment_valide(self, env_manager):
        """Test sync environnement valide"""
        mock_env = EnvironmentInfo("test", Path("/test"), "3.11")
        
        with patch.object(env_manager, 'get_environment_info', return_value=mock_env):
            with patch.object(env_manager.package_service, 'sync_environment') as mock_sync:
                mock_sync.return_value = SyncResult(success=True)
                
                result = env_manager.sync_environment("test")
                
                assert result.success is True
                mock_sync.assert_called_once_with(mock_env)

    def test_clone_environment_source_inexistant(self, env_manager):
        """Test clonage source inexistant"""
        with patch.object(env_manager, 'get_environment_info', return_value=None):
            result = env_manager.clone_environment("inexistant", "nouveau")
            
            assert result.success is False

    def test_clone_environment_cible_existe(self, env_manager):
        """Test clonage vers cible existante"""
        mock_source = EnvironmentInfo("source", Path("/test/source"), "3.11")
        
        with patch.object(env_manager, 'get_environment_info', side_effect=[mock_source, mock_source]):
            result = env_manager.clone_environment("source", "source")
            
            assert result.success is False

    def test_export_environment_format_requirements(self, env_manager):
        """Test export format requirements"""
        mock_env = EnvironmentInfo("test", Path("/test"), "3.11")
        
        with patch.object(env_manager, 'get_environment_info', return_value=mock_env):
            with patch.object(env_manager, '_export_to_requirements') as mock_export:
                mock_export.return_value = ExportResult(
                    success=True,
                    output_path=Path("/test/requirements.txt")
                )
                
                result = env_manager.export_environment("test", ExportFormat.REQUIREMENTS)
                
                assert result.success is True
                mock_export.assert_called_once()

    def test_import_environment_fichier_inexistant(self, env_manager):
        """Test import fichier inexistant"""
        with patch('pathlib.Path.exists', return_value=False):
            result = env_manager.import_environment(Path("/inexistant.txt"))
            
            assert result.success is False

    def test_doctor_environment_specifique(self, env_manager):
        """Test diagnostic environnement spécifique"""
        with patch.object(env_manager.diagnostic_service, 'diagnose_environment') as mock_diag:
            mock_report = DiagnosticReport(
                environment_name="test",
                overall_health=EnvironmentHealth.HEALTHY
            )
            mock_diag.return_value = mock_report
            
            result = env_manager.doctor_environment("test")
            
            assert result.environment_name == "test"
            mock_diag.assert_called_once_with("test")

    def test_doctor_environment_complet(self, env_manager):
        """Test diagnostic complet"""
        with patch.object(env_manager.diagnostic_service, 'run_full_diagnostic') as mock_diag:
            mock_report = DiagnosticReport(
                environment_name=None,
                overall_health=EnvironmentHealth.HEALTHY
            )
            mock_diag.return_value = mock_report
            
            result = env_manager.doctor_environment()
            
            assert result.environment_name is None
            mock_diag.assert_called_once()

    def test_auto_migrate_if_needed_succes(self, env_manager):
        """Test migration automatique succès"""
        with patch.object(env_manager.migration_service, 'auto_migrate_if_needed', return_value=True):
            result = env_manager.auto_migrate_if_needed()
            
            assert result is True

    def test_auto_migrate_if_needed_echec(self, env_manager):
        """Test migration automatique échec"""
        with patch.object(env_manager.migration_service, 'auto_migrate_if_needed', 
                         side_effect=Exception("Erreur migration")):
            result = env_manager.auto_migrate_if_needed()
            
            assert result is False

    def test_validate_environment_name_valide(self, env_manager):
        """Test validation nom valide"""
        # Ne devrait pas lever d'exception
        env_manager._validate_environment_name("valid_name")

    def test_validate_environment_name_invalide(self, env_manager):
        """Test validation nom invalide"""
        with patch('gestvenv.utils.ValidationUtils.validate_environment_name', return_value=False):
            with pytest.raises(ValidationError):
                env_manager._validate_environment_name("../invalid")

    def test_environment_exists_vrai(self, env_manager):
        """Test environnement existe"""
        with patch.object(env_manager, '_get_environment_path') as mock_path:
            mock_path.return_value = Path("/test/envs/test")
            with patch('pathlib.Path.exists', return_value=True):
                assert env_manager._environment_exists("test") is True

    def test_environment_exists_faux(self, env_manager):
        """Test environnement n'existe pas"""
        with patch.object(env_manager, '_get_environment_path') as mock_path:
            mock_path.return_value = Path("/test/envs/test")
            with patch('pathlib.Path.exists', return_value=False):
                assert env_manager._environment_exists("test") is False

    def test_get_environment_path(self, env_manager):
        """Test récupération chemin environnement"""
        env_manager.config_manager.config.environments_path = Path("/test/envs")
        
        path = env_manager._get_environment_path("test_env")
        
        assert path == Path("/test/envs/test_env")

    def test_lazy_loading_services(self, env_manager):
        """Test chargement paresseux des services"""
        # Vérification que les services ne sont pas chargés initialement
        assert not hasattr(env_manager, '_backend_manager')
        assert not hasattr(env_manager, '_package_service')
        assert not hasattr(env_manager, '_cache_service')
        
        # Accès aux propriétés déclenche le chargement
        with patch('gestvenv.backends.BackendManager'):
            _ = env_manager.backend_manager
            assert hasattr(env_manager, '_backend_manager')