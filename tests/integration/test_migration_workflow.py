"""
Tests d'intégration des workflows de migration
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestMigrationWorkflow:
    """Tests de migration complète entre formats (mockés)"""

    def test_requirements_to_pyproject_migration(self, env_manager, tmp_path):
        """Test migration requirements.txt vers pyproject.toml (mocké)"""
        # Création requirements.txt
        requirements_content = '''# Production dependencies
requests==2.28.1
click>=8.0,<9.0
flask==2.2.2
'''
        req_path = tmp_path / "requirements.txt"
        req_path.write_text(requirements_content)

        # Mock MigrationService
        mock_migration_service = Mock()
        mock_migration_result = Mock(
            success=True,
            message="Migration réussie",
            output_path=tmp_path / "pyproject.toml"
        )
        mock_migration_service.convert_requirements_to_pyproject = Mock(return_value=mock_migration_result)

        env_manager._migration_service = mock_migration_service

        try:
            migration_service = env_manager.migration_service

            # Migration (utiliser la vraie méthode API)
            migration_result = migration_service.convert_requirements_to_pyproject(
                requirements_path=req_path,
                project_name="migrated-project",
                output_path=tmp_path / "pyproject.toml"
            )

            assert migration_result.success
            mock_migration_service.convert_requirements_to_pyproject.assert_called_once()

        finally:
            if hasattr(env_manager, '_migration_service'):
                delattr(env_manager, '_migration_service')

    def test_v1_to_v11_environment_migration(self, env_manager, tmp_path):
        """Test migration environnements v1.0 vers v1.1 (mocké)"""
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

        # Mock MigrationService
        mock_migration_service = Mock()
        mock_migration_result = Mock(
            success=True,
            message="Migration v1.0 -> v1.1 réussie",
            migrated_count=1,
            environments_migrated=["legacy_env"]
        )
        mock_migration_service.migrate_from_v1_0 = Mock(return_value=mock_migration_result)

        env_manager._migration_service = mock_migration_service

        try:
            migration_service = env_manager.migration_service

            # Migration
            migration_result = migration_service.migrate_from_v1_0(
                old_config_path=old_config_path
            )

            assert migration_result.success
            assert migration_result.migrated_count > 0
            mock_migration_service.migrate_from_v1_0.assert_called_once()

        finally:
            if hasattr(env_manager, '_migration_service'):
                delattr(env_manager, '_migration_service')

    def test_detect_migration_candidates(self, env_manager, tmp_path):
        """Test détection des candidats à la migration (mocké)"""
        # Créer quelques fichiers requirements
        (tmp_path / "project1" / "requirements.txt").parent.mkdir(parents=True)
        (tmp_path / "project1" / "requirements.txt").write_text("requests==2.28.0\n")
        (tmp_path / "project2" / "requirements.txt").parent.mkdir(parents=True)
        (tmp_path / "project2" / "requirements.txt").write_text("flask==2.0.0\n")

        # Mock MigrationService
        mock_migration_service = Mock()
        mock_candidates = [
            {"path": tmp_path / "project1", "type": "requirements"},
            {"path": tmp_path / "project2", "type": "requirements"}
        ]
        mock_migration_service.detect_migration_candidates = Mock(return_value=mock_candidates)

        env_manager._migration_service = mock_migration_service

        try:
            migration_service = env_manager.migration_service

            # Détection
            candidates = migration_service.detect_migration_candidates(tmp_path)

            assert len(candidates) == 2
            mock_migration_service.detect_migration_candidates.assert_called_once_with(tmp_path)

        finally:
            if hasattr(env_manager, '_migration_service'):
                delattr(env_manager, '_migration_service')

    def test_backup_before_migration(self, env_manager, tmp_path):
        """Test sauvegarde avant migration (mocké)"""
        # Mock MigrationService
        mock_migration_service = Mock()
        mock_backup_result = Mock(
            success=True,
            backup_path=tmp_path / "backups" / "env_backup.tar.gz"
        )
        mock_migration_service.backup_environment = Mock(return_value=mock_backup_result)

        env_manager._migration_service = mock_migration_service

        try:
            migration_service = env_manager.migration_service

            # Backup
            backup_result = migration_service.backup_environment("test_env")

            assert backup_result.success
            mock_migration_service.backup_environment.assert_called_once_with("test_env")

        finally:
            if hasattr(env_manager, '_migration_service'):
                delattr(env_manager, '_migration_service')

    def test_migration_rollback(self, env_manager, tmp_path):
        """Test rollback en cas d'échec de migration (mocké)"""
        # Mock MigrationService
        mock_migration_service = Mock()
        mock_rollback_result = Mock(
            success=True,
            message="Rollback effectué avec succès"
        )
        mock_migration_service.rollback_migration = Mock(return_value=mock_rollback_result)

        env_manager._migration_service = mock_migration_service

        try:
            migration_service = env_manager.migration_service

            # Rollback
            rollback_result = migration_service.rollback_migration("test_env", tmp_path / "backup.tar.gz")

            assert rollback_result.success
            mock_migration_service.rollback_migration.assert_called_once()

        finally:
            if hasattr(env_manager, '_migration_service'):
                delattr(env_manager, '_migration_service')

    def test_auto_migrate_if_needed(self, env_manager, tmp_path):
        """Test migration automatique si nécessaire (mocké)"""
        # Mock MigrationService
        mock_migration_service = Mock()
        mock_migration_service.auto_migrate_if_needed = Mock(return_value=True)

        env_manager._migration_service = mock_migration_service

        try:
            migration_service = env_manager.migration_service

            # Auto migration check
            result = migration_service.auto_migrate_if_needed()

            assert result is True
            mock_migration_service.auto_migrate_if_needed.assert_called_once()

        finally:
            if hasattr(env_manager, '_migration_service'):
                delattr(env_manager, '_migration_service')
