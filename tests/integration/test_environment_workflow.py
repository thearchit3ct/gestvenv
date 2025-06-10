"""
Tests d'intégration des workflows d'environnement complets
"""

import pytest
import json
from pathlib import Path
from gestvenv.core.models import BackendType, SourceFileType

class TestEnvironmentWorkflow:
    """Tests des workflows d'environnement de bout en bout"""
    
    def test_create_environment_from_pyproject(self, env_manager, tmp_path, sample_pyproject_toml):
        """Test création environnement depuis pyproject.toml"""
        # Création fichier pyproject.toml
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(sample_pyproject_toml)
        
        # Création environnement
        result = env_manager.create_from_pyproject(
            pyproject_path=pyproject_path,
            env_name="test_pyproject"
        )
        
        assert result.success
        assert result.environment.name == "test_pyproject"
        assert result.environment.source_file_type == SourceFileType.PYPROJECT_TOML
        assert len(result.environment.packages) >= 2
        
        # Vérification packages installés
        package_names = [pkg.name for pkg in result.environment.packages]
        assert "requests" in package_names
        assert "click" in package_names
    
    def test_create_environment_from_requirements(self, env_manager, tmp_path, sample_requirements_txt):
        """Test création environnement depuis requirements.txt"""
        # Création fichier requirements.txt
        req_path = tmp_path / "requirements.txt"
        req_path.write_text(sample_requirements_txt)
        
        # Création environnement
        result = env_manager.create_from_requirements(
            requirements_path=req_path,
            env_name="test_requirements"
        )
        
        assert result.success
        assert result.environment.name == "test_requirements"
        assert result.environment.source_file_type == SourceFileType.REQUIREMENTS_TXT
        assert len(result.environment.packages) >= 3
    
    def test_environment_lifecycle_complete(self, env_manager):
        """Test cycle de vie complet d'un environnement"""
        # 1. Création
        create_result = env_manager.create_environment(
            name="lifecycle_test",
            python_version="3.11"
        )
        assert create_result.success
        
        # 2. Ajout packages
        env_info = env_manager.get_environment_info("lifecycle_test")
        install_result = env_manager.package_service.install_package(
            env_info, "requests"
        )
        assert install_result.success
        
        # 3. Activation
        activate_result = env_manager.activate_environment("lifecycle_test")
        assert activate_result.success
        
        # 4. Export
        export_result = env_manager.export_environment("lifecycle_test")
        assert export_result.success
        assert export_result.data
        
        # 5. Clone
        clone_result = env_manager.clone_environment("lifecycle_test", "lifecycle_clone")
        assert clone_result.success
        assert clone_result.environment.name == "lifecycle_clone"
        
        # 6. Synchronisation
        sync_result = env_manager.sync_environment("lifecycle_clone")
        assert sync_result.success
        
        # 7. Suppression
        delete_result = env_manager.remove_environment("lifecycle_test")
        assert delete_result.success
        assert not env_manager.get_environment_info("lifecycle_test")
    
    def test_multi_environment_workflow(self, env_manager):
        """Test gestion simultanée de plusieurs environnements"""
        # Création plusieurs environnements
        environments = ["dev", "test", "prod"]
        
        for env_name in environments:
            result = env_manager.create_environment(
                name=env_name,
                python_version="3.11"
            )
            assert result.success
        
        # Vérification liste
        env_list = env_manager.list_environments()
        assert len(env_list.environments) >= 3
        
        env_names = [env.name for env in env_list.environments]
        for env_name in environments:
            assert env_name in env_names
        
        # Test isolation
        dev_env = env_manager.get_environment_info("dev")
        test_env = env_manager.get_environment_info("test")
        
        assert dev_env.path != test_env.path
        assert dev_env.name != test_env.name
    
    def test_environment_error_handling(self, env_manager):
        """Test gestion d'erreurs dans les workflows"""
        # Tentative création environnement existant
        env_manager.create_environment("error_test", python_version="3.11")
        
        duplicate_result = env_manager.create_environment("error_test", python_version="3.11")
        assert not duplicate_result.success
        assert "existe déjà" in duplicate_result.message.lower()
        
        # Tentative activation environnement inexistant
        activate_result = env_manager.activate_environment("nonexistent")
        assert not activate_result.success
        
        # Tentative export environnement inexistant
        export_result = env_manager.export_environment("nonexistent")
        assert not export_result.success