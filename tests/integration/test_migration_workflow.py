"""
Tests d'intégration des workflows de migration
"""

import pytest
import json
from pathlib import Path

class TestMigrationWorkflow:
    """Tests de migration complète entre formats"""
    
    def test_requirements_to_pyproject_migration(self, env_manager, tmp_path):
        """Test migration requirements.txt vers pyproject.toml"""
        # Création requirements.txt complexe
        requirements_content = '''# Production dependencies
requests==2.28.1
click>=8.0,<9.0
flask[async]==2.2.2

# Dev dependencies (commentaires)
pytest==7.1.2  # Testing framework
black==22.3.0  # Code formatter
flake8>=4.0    # Linting

# Optional extras
psycopg2-binary==2.9.3; sys_platform != "win32"
'''
        req_path = tmp_path / "requirements.txt"
        req_path.write_text(requirements_content)
        
        # Migration
        migration_result = env_manager.migration_service.migrate_requirements_to_pyproject(
            requirements_path=req_path,
            project_name="migrated-project",
            target_path=tmp_path / "pyproject.toml"
        )
        
        assert migration_result.success
        assert (tmp_path / "pyproject.toml").exists()
        
        # Vérification contenu pyproject.toml généré
        pyproject_content = (tmp_path / "pyproject.toml").read_text()
        assert "requests" in pyproject_content
        assert "click" in pyproject_content
        assert "flask" in pyproject_content
        
        # Test création environnement depuis pyproject migré
        create_result = env_manager.create_from_pyproject(
            pyproject_path=tmp_path / "pyproject.toml",
            env_name="migrated_env"
        )
        assert create_result.success
        
        # Vérification packages installés
        env_info = create_result.environment
        package_names = [pkg.name for pkg in env_info.packages]
        assert "requests" in package_names
        assert "click" in package_names
    
    def test_v1_to_v11_environment_migration(self, env_manager, tmp_path):
        """Test migration environnements v1.0 vers v1.1"""
        # Simulation données v1.0
        v1_config = {
            "environments": {
                "legacy_env": {
                    "path": str(tmp_path / "legacy_env"),
                    "python_version": "3.9",
                    "packages": [
                        "requests==2.25.0",
                        "click==8.0.1"
                    ],
                    "created_at": "2024-01-15T10:30:00",
                    "backend": "pip"
                }
            },
            "config_version": "1.0"
        }
        
        # Sauvegarde config v1.0
        old_config_path = tmp_path / "old_config.json"
        old_config_path.write_text(json.dumps(v1_config, indent=2))
        
        # Migration
        migration_result = env_manager.migration_service.migrate_from_v1_0(
            old_config_path=old_config_path
        )
        assert migration_result.success
        assert migration_result.migrated_count > 0
        
        # Vérification environnement migré
        env_info = env_manager.get_environment_info("legacy_env")
        assert env_info is not None
        assert env_info.python_version == "3.9"
        assert len(env_info.packages) >= 2
    
    def test_poetry_to_gestvenv_migration(self, env_manager, tmp_path):
        """Test migration projet Poetry vers GestVenv"""
        # Création pyproject.toml Poetry
        poetry_content = '''[tool.poetry]
name = "poetry-project"
version = "0.1.0"
description = "Test project"
authors = ["Test Author <test@example.com>"]

[tool.poetry.dependencies]
python = "^3.9"
requests = "^2.28.0"
click = "^8.1.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.1.0"
black = "^22.3.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
'''
        poetry_path = tmp_path / "pyproject.toml"
        poetry_path.write_text(poetry_content)
        
        # Création poetry.lock simulé
        lock_content = '''# Poetry lock file content would be here
# This is a simplified version for testing
'''
        lock_path = tmp_path / "poetry.lock"
        lock_path.write_text(lock_content)
        
        # Migration Poetry vers GestVenv
        migration_result = env_manager.migration_service.migrate_from_poetry(
            project_path=tmp_path,
            env_name="poetry_migrated"
        )
        assert migration_result.success
        
        # Vérification environnement créé
        env_info = env_manager.get_environment_info("poetry_migrated")
        assert env_info is not None
        assert env_info.name == "poetry_migrated"
    
    def test_batch_migration_workflow(self, env_manager, tmp_path):
        """Test migration par lots de plusieurs projets"""
        # Création plusieurs projets à migrer
        projects = ["project1", "project2", "project3"]
        
        for project in projects:
            project_dir = tmp_path / project
            project_dir.mkdir()
            
            # Chaque projet a requirements.txt différent
            req_content = f'''requests==2.28.1
{project}-specific-package==1.0.0
'''
            (project_dir / "requirements.txt").write_text(req_content)
        
        # Migration par lots
        migration_results = []
        for project in projects:
            project_path = tmp_path / project
            result = env_manager.migration_service.migrate_project_batch(
                project_path=project_path,
                env_name=f"{project}_env"
            )
            migration_results.append(result)
        
        # Vérification toutes migrations réussies
        assert all(result.success for result in migration_results)
        
        # Vérification environnements créés
        env_list = env_manager.list_environments()
        env_names = [env.name for env in env_list.environments]
        
        for project in projects:
            assert f"{project}_env" in env_names
    
    def test_migration_rollback(self, env_manager, tmp_path):
        """Test rollback en cas d'échec de migration"""
        # Sauvegarde état initial
        initial_envs = env_manager.list_environments().environments
        initial_count = len(initial_envs)
        
        # Tentative migration avec fichier invalide
        invalid_req = tmp_path / "invalid_requirements.txt"
        invalid_req.write_text("invalid-package-syntax===broken")
        
        # Migration (doit échouer)
        migration_result = env_manager.migration_service.migrate_requirements_to_pyproject(
            requirements_path=invalid_req,
            project_name="broken-migration",
            target_path=tmp_path / "broken.toml"
        )
        
        # Vérification échec et rollback
        assert not migration_result.success
        
        # État doit être identique à l'initial
        final_envs = env_manager.list_environments().environments
        assert len(final_envs) == initial_count
        
        # Aucun fichier corrompu créé
        assert not (tmp_path / "broken.toml").exists()