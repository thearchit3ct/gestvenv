"""Tests pour le service PackageService."""

from typing import Any, Generator
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

import json
from pathlib import Path

from gestvenv.services.package_service import PackageService

class TestPackageService:
    """Tests pour le service PackageService."""
    
    @pytest.fixture
    def package_service(self) -> Generator[PackageService, Any, None]:
        """Fixture pour créer une instance du service."""
        service = PackageService()
        # Mock les services directement
        service.env_service = MagicMock()
        service.sys_service = MagicMock()
        yield service
    
    def test_install_packages(self, package_service: PackageService, mock_subprocess: MagicMock | AsyncMock) -> None:
        """Teste l'installation de packages."""
        # Mocker les dépendances
        package_service._get_environment_path = lambda name: Path("/path/to/environments/test_env")
        package_service.env_service.get_pip_executable.return_value = Path("/path/to/environments/test_env/bin/pip")
        
        # Simuler un succès d'installation
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Successfully installed flask-2.0.1"
        
        # Installer un package
        success, message = package_service.install_packages("test_env", ["flask"])
        
        # Vérifier le résultat
        assert success is True
        assert "succès" in message
        
        # Vérifier que subprocess.run a été appelé correctement
        mock_subprocess.assert_called_once()
        args, _ = mock_subprocess.call_args
        assert "pip" in str(args[0][0])
        assert "install" in args[0]
        assert "flask" in args[0]
        
        # Simuler un échec d'installation
        mock_subprocess.reset_mock()
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stderr = "Error: Could not find a version that satisfies the requirement"
        
        success, message = package_service.install_packages("test_env", ["nonexistent-package"])
        
        assert success is False
        assert "Échec" in message or "Error" in message
    
    def test_uninstall_packages(self, package_service: PackageService, mock_subprocess: MagicMock | AsyncMock) -> None:
        """Teste la désinstallation de packages."""
        # Mocker les dépendances
        package_service._get_environment_path = lambda name: Path("/path/to/environments/test_env")
        package_service.env_service.get_pip_executable.return_value = Path("/path/to/environments/test_env/bin/pip")
        
        # Simuler un succès de désinstallation
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Successfully uninstalled flask-2.0.1"
        
        # Désinstaller un package
        success, message = package_service.uninstall_packages("test_env", ["flask"])
        
        # Vérifier le résultat
        assert success is True
        assert "succès" in message
        
        # Vérifier que subprocess.run a été appelé correctement
        mock_subprocess.assert_called_once()
        args, _ = mock_subprocess.call_args
        assert "pip" in str(args[0][0])
        assert "uninstall" in args[0]
        assert "-y" in args[0]  # Confirmer automatiquement
        assert "flask" in args[0]
    
    def test_list_installed_packages(self, package_service: PackageService, mock_subprocess: MagicMock | AsyncMock, mock_package_list: list[dict[str, str]]) -> None:
        """Teste la récupération de la liste des packages installés."""
        # Mocker les dépendances
        package_service._get_environment_path = lambda name: Path("/path/to/environments/test_env")
        package_service.env_service.get_pip_executable.return_value = Path("/path/to/environments/test_env/bin/pip")
        
        # Simuler la sortie de pip list --format=json
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = json.dumps(mock_package_list)
        
        # Récupérer la liste des packages
        packages = package_service.list_installed_packages("test_env")
        
        # Vérifier le résultat
        assert len(packages) == 3
        assert packages[0]["name"] == "pytest"
        assert packages[0]["version"] == "6.2.5"
        assert packages[1]["name"] == "flask"
        assert packages[1]["version"] == "2.0.1"
        
        # Vérifier que subprocess.run a été appelé correctement
        mock_subprocess.assert_called_once()
        args, _ = mock_subprocess.call_args
        assert "pip" in str(args[0][0])
        assert "list" in args[0]
        assert "--format=json" in args[0]
    
    # def test_check_for_updates(self, package_service: PackageService, mock_subprocess: MagicMock | AsyncMock, mock_outdated_packages: list[dict[str, str]]) -> None:
    #     """Teste la vérification des mises à jour disponibles."""
    #     # Mocker les dépendances
    #     package_service._get_environment_path = lambda name: Path("/path/to/environments/test_env")
    #     package_service.env_service.get_pip_executable.return_value = Path("/path/to/environments/test_env/bin/pip")
        
    #     # Simuler la sortie de pip list --outdated --format=json
    #     mock_subprocess.return_value.returncode = 0
    #     mock_subprocess.return_value.stdout = json.dumps(mock_outdated_packages)
        
    #     # Vérifier les mises à jour
    #     updates = package_service.check_for_updates("test_env")
        
    #     # Vérifier le résultat
    #     assert len(updates) == 2
    #     assert updates[0]["name"] == "pytest"
    #     assert updates[0]["version"] == "6.2.5"
    #     assert updates[0]["latest_version"] == "7.0.0"
        
    #     # Vérifier que subprocess.run a été appelé correctement
    #     mock_subprocess.assert_called_once()
    #     args, _ = mock_subprocess.call_args
    #     assert "pip" in str(args[0][0])
    #     assert "list" in args[0]
    #     assert "--outdated" in args[0]
    #     assert "--format=json" in args[0]