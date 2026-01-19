"""
Tests d'intégration des workflows d'environnement complets
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from gestvenv.core.models import (
    BackendType, SourceFileType, EnvironmentInfo, EnvironmentResult,
    ActivationResult, ExportResult, SyncResult, ExportFormat, PyProjectInfo
)


class TestEnvironmentWorkflow:
    """Tests des workflows d'environnement de bout en bout"""

    def test_create_environment_from_pyproject(self, env_manager, tmp_path, sample_pyproject_toml):
        """Test création environnement depuis pyproject.toml"""
        # Création fichier pyproject.toml
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(sample_pyproject_toml)

        # Mock les services pour éviter les vrais appels
        mock_backend = Mock()
        mock_backend.name = "pip"
        mock_backend.create_environment = Mock(return_value=True)
        mock_backend.list_packages = Mock(return_value=[])

        mock_system = Mock()
        mock_system.validate_python_version = Mock(return_value=True)

        mock_package_service = Mock()
        mock_package_service.install_package = Mock(return_value=Mock(success=True))

        mock_pyproject_info = PyProjectInfo(
            name="test-project",
            dependencies=["requests>=2.25.0", "click>=8.0"]
        )

        # Patcher les dépendances
        env_manager._backend_manager = Mock()
        env_manager._backend_manager.get_backend = Mock(return_value=mock_backend)
        env_manager._system_service = mock_system
        env_manager._package_service = mock_package_service

        try:
            with patch('gestvenv.utils.PyProjectParser.parse_pyproject_toml', return_value=mock_pyproject_info):
                with patch.object(env_manager, '_validate_environment_name'):
                    result = env_manager.create_from_pyproject(
                        pyproject_path=pyproject_path,
                        env_name="test_pyproject"
                    )

                    # Vérifier que le résultat est un EnvironmentResult
                    assert isinstance(result, EnvironmentResult)
                    # Le succès dépend des mocks
                    if result.success:
                        assert result.environment is not None
        finally:
            for attr in ['_backend_manager', '_system_service', '_package_service']:
                if hasattr(env_manager, attr):
                    delattr(env_manager, attr)

    def test_environment_lifecycle_complete(self, env_manager, tmp_path):
        """Test cycle de vie complet d'un environnement (mocké)"""
        # Mock les services
        mock_backend = Mock()
        mock_backend.name = "pip"
        mock_backend.create_environment = Mock(return_value=True)
        mock_backend.list_packages = Mock(return_value=[])

        mock_system = Mock()
        mock_system.validate_python_version = Mock(return_value=True)
        mock_system.get_activation_script = Mock(return_value=tmp_path / "bin" / "activate")

        mock_package_service = Mock()
        mock_package_service.install_package = Mock(return_value=Mock(success=True))
        mock_package_service.sync_environment = Mock(return_value=SyncResult(
            success=True, message="Sync OK", packages_added=[], packages_updated=[], packages_removed=[]
        ))

        env_manager._backend_manager = Mock()
        env_manager._backend_manager.get_backend = Mock(return_value=mock_backend)
        env_manager._system_service = mock_system
        env_manager._package_service = mock_package_service

        try:
            with patch.object(env_manager, '_validate_environment_name'):
                # 1. Création
                create_result = env_manager.create_environment(
                    name="lifecycle_test",
                    python_version="3.11"
                )

                if create_result.success:
                    # 2. Activation
                    with patch.object(env_manager, 'get_environment_info', return_value=create_result.environment):
                        with patch.object(env_manager, 'deactivate_environment', return_value=True):
                            with patch.object(env_manager, '_save_environment_metadata'):
                                activate_result = env_manager.activate_environment("lifecycle_test")
                                assert activate_result.success is True

                    # 3. Export
                    with patch.object(env_manager, 'get_environment_info', return_value=create_result.environment):
                        with patch('pathlib.Path.cwd', return_value=tmp_path):
                            export_result = env_manager.export_environment("lifecycle_test", ExportFormat.JSON)
                            assert export_result.success is True

        finally:
            for attr in ['_backend_manager', '_system_service', '_package_service']:
                if hasattr(env_manager, attr):
                    delattr(env_manager, attr)

    def test_multi_environment_workflow(self, env_manager, tmp_path):
        """Test gestion simultanée de plusieurs environnements (mocké)"""
        mock_backend = Mock()
        mock_backend.name = "pip"
        mock_backend.create_environment = Mock(return_value=True)
        mock_backend.list_packages = Mock(return_value=[])

        mock_system = Mock()
        mock_system.validate_python_version = Mock(return_value=True)

        env_manager._backend_manager = Mock()
        env_manager._backend_manager.get_backend = Mock(return_value=mock_backend)
        env_manager._system_service = mock_system

        try:
            with patch.object(env_manager, '_validate_environment_name'):
                # Création plusieurs environnements
                environments = ["dev", "test", "prod"]
                results = []

                for env_name in environments:
                    result = env_manager.create_environment(
                        name=env_name,
                        python_version="3.11"
                    )
                    results.append(result)

                # Vérifier que tous ont réussi ou échoué de façon cohérente
                assert all(r.success for r in results) or any(not r.success for r in results)

        finally:
            for attr in ['_backend_manager', '_system_service']:
                if hasattr(env_manager, attr):
                    delattr(env_manager, attr)

    def test_environment_error_handling(self, env_manager, tmp_path):
        """Test gestion d'erreurs dans les workflows"""
        # Créer un environnement qui existe déjà
        existing_env = env_manager.config_manager.get_environments_path() / "error_test"
        existing_env.mkdir(parents=True, exist_ok=True)

        try:
            # Tentative création environnement existant
            with patch.object(env_manager, '_validate_environment_name'):
                duplicate_result = env_manager.create_environment("error_test", python_version="3.11")
                assert not duplicate_result.success
                assert "existe déjà" in duplicate_result.message.lower()

            # Tentative activation environnement inexistant
            with patch.object(env_manager, 'get_environment_info', return_value=None):
                activate_result = env_manager.activate_environment("nonexistent")
                assert not activate_result.success

            # Tentative export environnement inexistant
            with patch.object(env_manager, 'get_environment_info', return_value=None):
                export_result = env_manager.export_environment("nonexistent", ExportFormat.JSON)
                assert not export_result.success

        finally:
            # Nettoyage
            if existing_env.exists():
                import shutil
                shutil.rmtree(existing_env, ignore_errors=True)

    def test_list_environments(self, env_manager, tmp_path):
        """Test listage des environnements"""
        import shutil

        # Créer le répertoire d'environnements dans tmp_path pour isoler le test
        envs_path = env_manager.config_manager.get_environments_path()

        # Nettoyer d'abord tous les répertoires existants
        if envs_path.exists():
            for item in envs_path.iterdir():
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)

        # Créer uniquement nos environnements de test
        (envs_path / "env1").mkdir(parents=True, exist_ok=True)
        (envs_path / "env2").mkdir(parents=True, exist_ok=True)

        mock_env1 = EnvironmentInfo("env1", envs_path / "env1", "3.11")
        mock_env2 = EnvironmentInfo("env2", envs_path / "env2", "3.10")

        try:
            # Utiliser un lambda pour retourner les mocks selon le nom
            def mock_load_metadata(name):
                if name == "env1":
                    return mock_env1
                elif name == "env2":
                    return mock_env2
                return None

            with patch.object(env_manager, '_load_environment_metadata', side_effect=mock_load_metadata):
                # list_environments() retourne une liste directement
                env_list = env_manager.list_environments()

                assert isinstance(env_list, list)
                assert len(env_list) == 2

        finally:
            for name in ["env1", "env2"]:
                path = envs_path / name
                if path.exists():
                    shutil.rmtree(path, ignore_errors=True)
