"""Tests pour le service PackageService."""

import os
import json
import pytest
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from typing import List, Dict, Any

from gestvenv.services.package_service import PackageService

class TestPackageService:
    """Tests pour la classe PackageService."""
    
    @pytest.fixture
    def package_service(self) -> PackageService:
        """Fixture pour créer une instance du service de packages."""
        with patch('gestvenv.services.package_service.EnvironmentService'), \
             patch('gestvenv.services.package_service.SystemService'), \
             patch('gestvenv.services.package_service.CacheService'), \
             patch('gestvenv.core.config_manager.ConfigManager'):
            return PackageService()
    
    @pytest.fixture
    def mock_env_path(self, temp_dir: Path) -> Path:
        """Fixture pour créer un chemin d'environnement simulé."""
        env_path = temp_dir / "test_env"
        env_path.mkdir(parents=True, exist_ok=True)
        return env_path
    
    @pytest.fixture
    def mock_pip_exe(self, mock_env_path: Path) -> Path:
        """Fixture pour créer un exécutable pip simulé."""
        if os.name == "nt":
            pip_path = mock_env_path / "Scripts" / "pip.exe"
            pip_path.parent.mkdir(exist_ok=True)
        else:
            pip_path = mock_env_path / "bin" / "pip"
            pip_path.parent.mkdir(exist_ok=True)
        
        pip_path.touch()
        return pip_path
    
    def test_init(self, package_service: PackageService) -> None:
        """Teste l'initialisation du service."""
        assert package_service.env_service is not None
        assert package_service.sys_service is not None
        assert package_service.cache_service is not None
        assert isinstance(package_service.offline_mode, bool)
        assert isinstance(package_service.use_cache, bool)
    
    @patch('subprocess.run')
    def test_install_packages_success(self, mock_subprocess: MagicMock, 
                                     package_service: PackageService,
                                     mock_pip_exe: Path) -> None:
        """Teste l'installation réussie de packages."""
        # Configurer les mocks
        package_service.env_service.get_pip_executable.return_value = mock_pip_exe
        package_service._get_environment_path = MagicMock(return_value=mock_pip_exe.parent.parent)
        
        # Configurer subprocess pour retourner un succès
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Successfully installed packages"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        # Tester l'installation
        # Mock du cache pour éviter l\'erreur
        package_service.cache_service.check_offline_availability.return_value = ([], ["flask", "pytest"])
        success, message = package_service.install_packages("test_env", "flask,pytest")
        
        assert success is True
        assert "succès" in message
        mock_subprocess.assert_called_once()
    
    @patch('subprocess.run')
    def test_install_packages_failure(self, mock_subprocess: MagicMock,
                                     package_service: PackageService,
                                     mock_pip_exe: Path) -> None:
        """Teste l'échec d'installation de packages."""
        # Configurer les mocks
        package_service.env_service.get_pip_executable.return_value = mock_pip_exe
        package_service._get_environment_path = MagicMock(return_value=mock_pip_exe.parent.parent)
        
        # Configurer subprocess pour retourner une erreur
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Package installation failed"
        mock_subprocess.return_value = mock_result
        
        # Tester l'installation
        # Mock du cache pour éviter l\'erreur
        package_service.cache_service.check_offline_availability.return_value = ([], ["flask", "pytest"])
        success, message = package_service.install_packages("test_env", "invalid-package")
        
        assert success is False
        assert 'Erreur' in message or 'Échec' in message
    
    def test_install_packages_no_environment(self, package_service: PackageService) -> None:
        """Teste l'installation dans un environnement inexistant."""
        package_service._get_environment_path = MagicMock(return_value=None)
        # Mock du cache pour éviter l\'erreur
        package_service.cache_service.check_offline_availability.return_value = ([], ["flask", "pytest"])
        
        success, message = package_service.install_packages("nonexistent_env", "flask")
        
        assert success is False
        assert "non trouvé" in message
    
    def test_install_packages_no_pip(self, package_service: PackageService,
                                    mock_env_path: Path) -> None:
        """Teste l'installation sans pip disponible."""
        package_service._get_environment_path = MagicMock(return_value=mock_env_path)
        package_service.env_service.get_pip_executable.return_value = None
        # Mock du cache pour éviter l\'erreur
        package_service.cache_service.check_offline_availability.return_value = ([], ["flask", "pytest"])
        
        success, message = package_service.install_packages("test_env", "flask")
        
        assert success is False
        assert "pip non trouvé" in message
    
    @patch('subprocess.run')
    def test_uninstall_packages_success(self, mock_subprocess: MagicMock,
                                       package_service: PackageService,
                                       mock_pip_exe: Path) -> None:
        """Teste la désinstallation réussie de packages."""
        # Configurer les mocks
        package_service._get_environment_path = MagicMock(return_value=mock_pip_exe.parent.parent)
        package_service.env_service.get_pip_executable.return_value = mock_pip_exe
        
        # Configurer subprocess pour retourner un succès
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        # Tester la désinstallation
        success, message = package_service.uninstall_packages("test_env", "flask,pytest")
        
        assert success is True
        assert "succès" in message
        mock_subprocess.assert_called_once()
    
    @patch('subprocess.run')
    def test_update_packages_success(self, mock_subprocess: MagicMock,
                                    package_service: PackageService,
                                    mock_pip_exe: Path) -> None:
        """Teste la mise à jour réussie de packages."""
        # Configurer les mocks
        package_service._get_environment_path = MagicMock(return_value=mock_pip_exe.parent.parent)
        package_service.env_service.get_pip_executable.return_value = mock_pip_exe
        
        # Mock pour list_installed_packages
        mock_packages = [{"name": "flask", "version": "2.0.1"}]
        package_service.list_installed_packages = MagicMock(return_value=mock_packages)
        
        # Configurer subprocess pour retourner un succès
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        # Tester la mise à jour de tous les packages
        success, message = package_service.update_packages("test_env", all_packages=True)
        
        assert success is True
        assert "succès" in message
        mock_subprocess.assert_called_once()
    
    @patch('subprocess.run')
    def test_list_installed_packages_success(self, mock_subprocess: MagicMock,
                                           package_service: PackageService,
                                           mock_pip_exe: Path) -> None:
        """Teste la récupération réussie de la liste des packages installés."""
        # Configurer les mocks
        package_service._get_environment_path = MagicMock(return_value=mock_pip_exe.parent.parent)
        package_service.env_service.get_pip_executable.return_value = mock_pip_exe
        
        # Simuler la sortie JSON de pip list
        mock_packages = [
            {"name": "flask", "version": "2.0.1"},
            {"name": "pytest", "version": "6.2.5"}
        ]
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(mock_packages)
        mock_subprocess.return_value = mock_result
        
        # Tester la récupération
        packages = package_service.list_installed_packages("test_env")
        
        assert len(packages) == 2
        assert packages[0]["name"] == "flask"
        assert packages[1]["name"] == "pytest"
        mock_subprocess.assert_called_once()
    
    @patch('subprocess.run')
    def test_list_installed_packages_failure(self, mock_subprocess: MagicMock,
                                           package_service: PackageService,
                                           mock_pip_exe: Path) -> None:
        """Teste l'échec de récupération de la liste des packages."""
        # Configurer les mocks
        package_service._get_environment_path = MagicMock(return_value=mock_pip_exe.parent.parent)
        package_service.env_service.get_pip_executable.return_value = mock_pip_exe
        
        # Configurer subprocess pour retourner une erreur
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Error listing packages"
        mock_subprocess.return_value = mock_result
        
        # Tester la récupération
        packages = package_service.list_installed_packages("test_env")
        
        assert packages == []
    
    @patch('subprocess.run')
    def test_show_package_info_success(self, mock_subprocess: MagicMock,
                                      package_service: PackageService,
                                      mock_pip_exe: Path) -> None:
        """Teste la récupération réussie d'informations sur un package."""
        # Configurer les mocks
        package_service._get_environment_path = MagicMock(return_value=mock_pip_exe.parent.parent)
        package_service.env_service.get_pip_executable.return_value = mock_pip_exe
        
        # Simuler la sortie de pip show
        mock_output = """Name: flask
Version: 2.0.1
Summary: A simple framework for building complex web applications.
Requires: click, werkzeug
Required-by: 
"""
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = mock_output
        mock_subprocess.return_value = mock_result
        
        # Tester la récupération
        info = package_service.show_package_info("flask", "test_env")
        
        assert info is not None
        assert info["name"] == "flask"
        assert info["version"] == "2.0.1"
        assert "click" in info["requires"]
        assert "werkzeug" in info["requires"]
        assert info["required_by"] == []
    
    @patch('subprocess.run')
    def test_export_requirements_success(self, mock_subprocess: MagicMock,
                                        package_service: PackageService,
                                        mock_pip_exe: Path, temp_dir: Path) -> None:
        """Teste l'export réussi d'un fichier requirements.txt."""
        # Configurer les mocks
        package_service._get_environment_path = MagicMock(return_value=mock_pip_exe.parent.parent)
        package_service.env_service.get_pip_executable.return_value = mock_pip_exe
        
        # Simuler la sortie de pip freeze
        mock_output = "flask==2.0.1\npytest==6.2.5\n"
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = mock_output
        mock_subprocess.return_value = mock_result
        
        # Tester l'export
        output_path = temp_dir / "requirements.txt"
        success, path = package_service.export_requirements("test_env", output_path)
        
        assert success is True
        assert str(output_path) in path
        assert output_path.exists()
        
        # Vérifier le contenu
        content = output_path.read_text()
        assert "flask==2.0.1" in content
        assert "pytest==6.2.5" in content
    
    @patch('subprocess.run')
    def test_check_for_updates_success(self, mock_subprocess: MagicMock,
                                      package_service: PackageService,
                                      mock_pip_exe: Path) -> None:
        """Teste la vérification réussie des mises à jour."""
        # Configurer les mocks
        package_service._get_environment_path = MagicMock(return_value=mock_pip_exe.parent.parent)
        package_service.env_service.get_pip_executable.return_value = mock_pip_exe
        
        # Simuler la sortie JSON de pip list --outdated
        mock_updates = [
            {
                "name": "flask",
                "version": "2.0.1",
                "latest_version": "2.1.0"
            }
        ]
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(mock_updates)
        mock_subprocess.return_value = mock_result
        
        # Tester la vérification
        updates = package_service.check_for_updates("test_env")
        
        assert len(updates) == 1
        assert updates[0]["name"] == "flask"
        assert updates[0]["current_version"] == "2.0.1"
        assert updates[0]["latest_version"] == "2.1.0"
    
    def test_check_package_dependencies(self, package_service: PackageService) -> None:
        """Teste la vérification des dépendances d'un package."""
        # Mock de show_package_info
        mock_info = {
            "name": "flask",
            "version": "2.0.1",
            "required_by": ["my-app", "web-service"]
        }
        package_service.show_package_info = MagicMock(return_value=mock_info)
        
        # Tester la vérification
        dependencies = package_service.check_package_dependencies("test_env", "flask")
        
        assert "flask" in dependencies
        assert "my-app" in dependencies["flask"]
        assert "web-service" in dependencies["flask"]
    
    def test_install_from_requirements_file(self, package_service: PackageService,
                                           temp_dir: Path) -> None:
        """Teste l'installation depuis un fichier requirements.txt."""
        # Créer un fichier requirements.txt
        requirements_file = temp_dir / "requirements.txt"
        requirements_file.write_text("flask==2.0.1\npytest==6.2.5\n")
        
        # Mock de la méthode helper
        package_service._install_from_requirements_file = MagicMock(
            return_value=(True, "Installation réussie")
        )
        package_service._get_environment_path = MagicMock(return_value=temp_dir)
        package_service.env_service.get_pip_executable.return_value = temp_dir / "pip"
        
        # Tester l'installation
        success, message = package_service.install_from_requirements("test_env", requirements_file)
        
        assert success is True
        assert "réussie" in message
    
    def test_install_from_requirements_file_not_exists(self, package_service: PackageService,
                                                      temp_dir: Path) -> None:
        """Teste l'installation depuis un fichier requirements.txt inexistant."""
        nonexistent_file = temp_dir / "nonexistent.txt"
        
        success, message = package_service.install_from_requirements("test_env", nonexistent_file)
        
        assert success is False
        assert "n'existe pas" in message
    
    def test_check_offline_availability(self, package_service: PackageService) -> None:
        """Teste la vérification de disponibilité hors ligne."""
        # Mock du cache service
        package_service.cache_service.has_package = MagicMock(side_effect=lambda name, version: name == "flask")
        
        # Tester avec une liste de packages
        availability = package_service.check_offline_availability("flask,pytest")
        
        assert "flask" in availability
        assert "pytest" in availability
        assert availability["flask"] is True
        assert availability["pytest"] is False
    
    def test_check_offline_availability_requirements_file(self, package_service: PackageService,
                                                         temp_dir: Path) -> None:
        """Teste la vérification de disponibilité hors ligne avec fichier requirements."""
        # Créer un fichier requirements.txt
        requirements_file = temp_dir / "requirements.txt"
        requirements_file.write_text("flask==2.0.1\npytest==6.2.5\n")
        
        # Mock du cache service
        package_service.cache_service.has_package = MagicMock(return_value=True)
        
        # Tester avec un fichier requirements
        availability = package_service.check_offline_availability(requirements_file)
        
        assert "flask==2.0.1" in availability
        assert "pytest==6.2.5" in availability
        assert availability["flask==2.0.1"] is True
        assert availability["pytest==6.2.5"] is True
    
    def test_get_package_size(self, package_service: PackageService) -> None:
        """Teste la récupération de la taille d'un package."""
        # Mock du cache service
        mock_index = {
            "flask": {
                "versions": {
                    "2.0.1": {"size": 1024000}
                }
            }
        }
        package_service.cache_service.index = mock_index
        
        # Tester la récupération de taille
        size = package_service.get_package_size("flask", "2.0.1")
        assert size == 1024000
        
        # Tester avec package inexistant
        size = package_service.get_package_size("nonexistent")
        assert size is None
    
    def test_extract_package_info(self, package_service: PackageService) -> None:
        """Teste l'extraction d'informations depuis un nom de fichier."""
        # Test avec fichier wheel
        info = package_service._extract_package_info("flask-2.0.1-py3-none-any.whl")
        assert info["name"] == "flask"
        assert info["version"] == "2.0.1"
        
        # Test avec fichier tar.gz
        info = package_service._extract_package_info("pytest-6.2.5.tar.gz")
        assert info["name"] == "pytest"
        assert info["version"] == "6.2.5"
        
        # Test avec nom invalide
        info = package_service._extract_package_info("invalid")
        if info is not None:
            assert info["name"] == "invalid"
        else:
            assert info is None
        assert info["version"] == "unknown"
    
    @patch('subprocess.run')
    def test_get_package_dependencies(self, mock_subprocess: MagicMock,
                                     package_service: PackageService) -> None:
        """Teste la récupération des dépendances d'un package."""
        # Simuler la sortie de pip show
        mock_output = """Name: flask
Version: 2.0.1
Requires: click, werkzeug
"""
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = mock_output
        mock_subprocess.return_value = mock_result
        
        # Tester la récupération
        dependencies = package_service._get_package_dependencies("flask")
        
        assert "click" in dependencies
        assert "werkzeug" in dependencies
    
    def test_separate_cached_packages(self, package_service: PackageService) -> None:
        """Teste la séparation des packages selon leur disponibilité dans le cache."""
        # Mock du cache service
        package_service.cache_service.has_package = MagicMock(
            side_effect=lambda name, version: name == "flask"
        )
        
        packages = ["flask==2.0.1", "pytest==6.2.5"]
        cached, non_cached = package_service._separate_cached_packages(packages)
        
        assert "flask==2.0.1" in cached
        assert "pytest==6.2.5" in non_cached
    
    def test_get_environment_path_success(self, package_service: PackageService,
                                         temp_dir: Path) -> None:
        """Teste la récupération réussie du chemin d'un environnement."""
        # Mock du config manager
        mock_env_info = MagicMock()
        mock_env_info.path = temp_dir / "test_env"
        package_service.config_manager = MagicMock()
        package_service.config_manager.get_environment.return_value = mock_env_info
        
        path = package_service._get_environment_path("test_env")
        
        assert path == mock_env_info.path
    
    def test_get_environment_path_failure(self, package_service: PackageService) -> None:
        """Teste l'échec de récupération du chemin d'un environnement."""
        # Mock du config manager qui retourne None
        package_service.config_manager = MagicMock()
        package_service.config_manager.get_environment.return_value = None
        
        # Mock de l'environnement service
        package_service.env_service.get_default_venv_dir.return_value = Path("/default")
        
        path = package_service._get_environment_path("nonexistent")
        
        assert path is None
    
    def test_install_packages_with_requirements_file(self, package_service: PackageService,
                                                    mock_pip_exe: Path, temp_dir: Path) -> None:
        """Teste l'installation avec un fichier requirements."""
        # Créer un fichier requirements
        requirements_file = temp_dir / "requirements.txt"
        requirements_file.write_text("flask==2.0.1\n")
        
        # Configurer les mocks
        package_service._get_environment_path = MagicMock(return_value=mock_pip_exe.parent.parent)
        package_service.env_service.get_pip_executable.return_value = mock_pip_exe
        package_service._install_from_requirements_file = MagicMock(
            return_value=(True, "Installation réussie")
        )
        
        # Tester l'installation
        # Mock du cache pour éviter l\'erreur
        package_service.cache_service.check_offline_availability.return_value = ([], ["flask", "pytest"])
        success, message = package_service.install_packages(
            "test_env", None, requirements_file=requirements_file
        )
        
        assert success is True
        assert "réussie" in message
        package_service._install_from_requirements_file.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])