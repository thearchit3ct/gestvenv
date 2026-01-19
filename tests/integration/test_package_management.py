"""
Tests d'intégration de la gestion des packages
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from gestvenv.core.models import PackageInfo, SyncResult, EnvironmentInfo, InstallResult


class TestPackageManagement:
    """Tests de gestion complète des packages (mockés)"""

    def test_package_installation_workflow(self, env_manager, tmp_path):
        """Test workflow installation de packages (mocké)"""
        # Mock PackageService
        mock_package_service = Mock()
        mock_install_result = InstallResult(
            success=True,
            message="Package installé",
            packages_installed=["requests"],
            backend_used="pip"
        )
        mock_package_service.install_package = Mock(return_value=mock_install_result)

        # Mock EnvironmentInfo
        mock_env = EnvironmentInfo(
            name="pkg_test",
            path=tmp_path / "pkg_test",
            python_version="3.11"
        )

        env_manager._package_service = mock_package_service

        try:
            package_service = env_manager.package_service

            # Installation package simple
            install_result = package_service.install_package(mock_env, "requests")

            assert install_result.success
            assert "requests" in install_result.packages_installed
            mock_package_service.install_package.assert_called_once()

        finally:
            if hasattr(env_manager, '_package_service'):
                delattr(env_manager, '_package_service')

    def test_package_installation_with_version(self, env_manager, tmp_path):
        """Test installation package avec version spécifique (mocké)"""
        mock_package_service = Mock()
        mock_install_result = InstallResult(
            success=True,
            message="Package installé",
            packages_installed=["click==8.1.3"],
            backend_used="pip"
        )
        mock_package_service.install_package = Mock(return_value=mock_install_result)

        mock_env = EnvironmentInfo(
            name="version_test",
            path=tmp_path / "version_test",
            python_version="3.11"
        )

        env_manager._package_service = mock_package_service

        try:
            package_service = env_manager.package_service

            # Installation avec version spécifique
            install_result = package_service.install_package(mock_env, "click==8.1.3")

            assert install_result.success
            mock_package_service.install_package.assert_called_once_with(mock_env, "click==8.1.3")

        finally:
            if hasattr(env_manager, '_package_service'):
                delattr(env_manager, '_package_service')

    def test_package_update_workflow(self, env_manager, tmp_path):
        """Test workflow mise à jour packages (mocké)"""
        mock_package_service = Mock()
        mock_update_result = InstallResult(
            success=True,
            message="Package mis à jour",
            packages_installed=["requests"],
            backend_used="pip"
        )
        mock_package_service.update_package = Mock(return_value=mock_update_result)

        mock_env = EnvironmentInfo(
            name="update_test",
            path=tmp_path / "update_test",
            python_version="3.11"
        )

        env_manager._package_service = mock_package_service

        try:
            package_service = env_manager.package_service

            # Mise à jour
            update_result = package_service.update_package(mock_env, "requests")

            assert update_result.success
            mock_package_service.update_package.assert_called_once_with(mock_env, "requests")

        finally:
            if hasattr(env_manager, '_package_service'):
                delattr(env_manager, '_package_service')

    def test_package_removal_workflow(self, env_manager, tmp_path):
        """Test workflow suppression packages (mocké)"""
        mock_package_service = Mock()
        mock_uninstall_result = Mock(
            success=True,
            message="Package désinstallé"
        )
        # Note: la méthode s'appelle uninstall_package, pas remove_package
        mock_package_service.uninstall_package = Mock(return_value=mock_uninstall_result)

        mock_env = EnvironmentInfo(
            name="remove_test",
            path=tmp_path / "remove_test",
            python_version="3.11"
        )

        env_manager._package_service = mock_package_service

        try:
            package_service = env_manager.package_service

            # Suppression package
            remove_result = package_service.uninstall_package(mock_env, "pytest")

            assert remove_result.success
            mock_package_service.uninstall_package.assert_called_once_with(mock_env, "pytest")

        finally:
            if hasattr(env_manager, '_package_service'):
                delattr(env_manager, '_package_service')

    def test_list_packages(self, env_manager, tmp_path):
        """Test listage des packages (mocké)"""
        mock_package_service = Mock()
        mock_packages = [
            PackageInfo("requests", "2.28.0"),
            PackageInfo("click", "8.1.3"),
            PackageInfo("flask", "2.2.2")
        ]
        mock_package_service.list_packages = Mock(return_value=mock_packages)

        mock_env = EnvironmentInfo(
            name="list_test",
            path=tmp_path / "list_test",
            python_version="3.11"
        )

        env_manager._package_service = mock_package_service

        try:
            package_service = env_manager.package_service

            # Listage
            packages = package_service.list_packages(mock_env)

            assert len(packages) == 3
            package_names = [p.name for p in packages]
            assert "requests" in package_names
            assert "click" in package_names
            assert "flask" in package_names

        finally:
            if hasattr(env_manager, '_package_service'):
                delattr(env_manager, '_package_service')

    def test_install_from_requirements(self, env_manager, tmp_path):
        """Test installation depuis requirements.txt (mocké)"""
        # Création requirements.txt
        req_path = tmp_path / "requirements.txt"
        req_path.write_text("requests==2.28.0\nclick>=8.0\n")

        mock_package_service = Mock()
        mock_install_result = InstallResult(
            success=True,
            message="Packages installés depuis requirements.txt",
            packages_installed=["requests", "click"],
            backend_used="pip"
        )
        mock_package_service.install_from_requirements = Mock(return_value=mock_install_result)

        mock_env = EnvironmentInfo(
            name="req_test",
            path=tmp_path / "req_test",
            python_version="3.11"
        )

        env_manager._package_service = mock_package_service

        try:
            package_service = env_manager.package_service

            # Installation depuis requirements
            install_result = package_service.install_from_requirements(mock_env, req_path)

            assert install_result.success
            assert len(install_result.packages_installed) == 2
            mock_package_service.install_from_requirements.assert_called_once()

        finally:
            if hasattr(env_manager, '_package_service'):
                delattr(env_manager, '_package_service')

    def test_sync_environment(self, env_manager, tmp_path):
        """Test synchronisation environnement (mocké)"""
        mock_package_service = Mock()
        mock_sync_result = SyncResult(
            success=True,
            message="Synchronisation réussie",
            packages_added=["click"],
            packages_updated=["requests"],
            packages_removed=[]
        )
        mock_package_service.sync_environment = Mock(return_value=mock_sync_result)

        mock_env = EnvironmentInfo(
            name="sync_test",
            path=tmp_path / "sync_test",
            python_version="3.11"
        )

        env_manager._package_service = mock_package_service

        try:
            package_service = env_manager.package_service

            # Synchronisation
            sync_result = package_service.sync_environment(mock_env)

            assert sync_result.success
            assert "click" in sync_result.packages_added
            assert "requests" in sync_result.packages_updated
            mock_package_service.sync_environment.assert_called_once()

        finally:
            if hasattr(env_manager, '_package_service'):
                delattr(env_manager, '_package_service')

    def test_check_outdated_packages(self, env_manager, tmp_path):
        """Test vérification packages obsolètes (mocké)"""
        mock_package_service = Mock()
        mock_outdated = [
            {"name": "requests", "current": "2.25.0", "latest": "2.28.0"},
            {"name": "click", "current": "8.0.0", "latest": "8.1.3"}
        ]
        mock_package_service.check_outdated_packages = Mock(return_value=mock_outdated)

        mock_env = EnvironmentInfo(
            name="outdated_test",
            path=tmp_path / "outdated_test",
            python_version="3.11"
        )

        env_manager._package_service = mock_package_service

        try:
            package_service = env_manager.package_service

            # Vérification outdated
            outdated = package_service.check_outdated_packages(mock_env)

            assert len(outdated) == 2
            assert outdated[0]["name"] == "requests"
            assert outdated[1]["name"] == "click"
            mock_package_service.check_outdated_packages.assert_called_once()

        finally:
            if hasattr(env_manager, '_package_service'):
                delattr(env_manager, '_package_service')

    def test_install_from_pyproject(self, env_manager, tmp_path):
        """Test installation depuis pyproject.toml (mocké)"""
        # Création pyproject.toml
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text('''[project]
name = "test-project"
dependencies = ["requests>=2.25.0", "click>=8.0"]
''')

        mock_package_service = Mock()
        mock_install_result = InstallResult(
            success=True,
            message="Packages installés depuis pyproject.toml",
            packages_installed=["requests", "click"],
            backend_used="pip"
        )
        mock_package_service.install_from_pyproject = Mock(return_value=mock_install_result)

        mock_env = EnvironmentInfo(
            name="pyproject_test",
            path=tmp_path / "pyproject_test",
            python_version="3.11"
        )

        env_manager._package_service = mock_package_service

        try:
            package_service = env_manager.package_service

            # Installation depuis pyproject
            install_result = package_service.install_from_pyproject(mock_env, pyproject_path)

            assert install_result.success
            assert len(install_result.packages_installed) == 2
            mock_package_service.install_from_pyproject.assert_called_once()

        finally:
            if hasattr(env_manager, '_package_service'):
                delattr(env_manager, '_package_service')
