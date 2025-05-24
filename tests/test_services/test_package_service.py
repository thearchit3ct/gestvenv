import os
import pytest
import tempfile
import shutil
from unittest.mock import MagicMock, patch, AsyncMock, ANY
from pathlib import Path

from gestvenv.services.package_service import PackageService


@pytest.fixture
def mock_subprocess():
    """Fixture pour mocker subprocess.run."""
    with patch("subprocess.run") as mock:
        yield mock


@pytest.fixture
def package_service():
    """Fixture pour créer une instance de PackageService avec des mocks."""
    service = PackageService()
    
    # Mocker les services dépendants
    service.env_service = MagicMock()
    service.sys_service = MagicMock()
    service.cache_service = MagicMock()
    
    # Configurer le mode hors ligne et l'utilisation du cache
    service.offline_mode = False
    service.use_cache = True
    
    return service


class TestPackageService:
    """Tests pour le service de gestion des packages."""

    def test_install_packages(self, package_service: PackageService, mock_subprocess: MagicMock | AsyncMock) -> None:
        """Teste l'installation de packages."""
        # Mocker les dépendances
        package_service._get_environment_path = lambda name: Path("/path/to/environments/test_env")
        package_service.env_service.get_pip_executable.return_value = Path("/path/to/environments/test_env/bin/pip")
        
        # Désactiver l'utilisation du cache pour ce test pour simplifier
        package_service.use_cache = False
    
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
        mock_subprocess.assert_called_with(
            [str(Path("/path/to/environments/test_env/bin/pip")), "install", "flask"],
            capture_output=True,
            text=True,
            shell=False,
            check=False
        )

    def test_install_packages_with_cache(self, package_service: PackageService, mock_subprocess: MagicMock | AsyncMock) -> None:
        """Teste l'installation de packages avec le cache activé."""
        # Mocker les dépendances
        package_service._get_environment_path = lambda name: Path("/path/to/environments/test_env")
        package_service.env_service.get_pip_executable.return_value = Path("/path/to/environments/test_env/bin/pip")
        
        # Activer l'utilisation du cache
        package_service.use_cache = True
        package_service.offline_mode = False
        
        # Simuler que le package n'est pas dans le cache
        package_service.cache_service.has_package.return_value = False
        
        # Simuler un succès d'installation et de téléchargement
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Successfully installed flask-2.0.1"
    
        # Installer un package
        success, message = package_service.install_packages("test_env", ["flask"])
    
        # Vérifier le résultat
        assert success is True
        assert "succès" in message
    
        # Vérifier que subprocess.run a été appelé deux fois (téléchargement puis installation)
        assert mock_subprocess.call_count == 2
        
        # Vérifier les appels
        calls = mock_subprocess.call_args_list
        
        # Premier appel: téléchargement pour le cache
        assert calls[0][0][0][0:3] == [
            str(Path("/path/to/environments/test_env/bin/pip")), 
            "install", 
            "--dest"
        ]
        
        # Deuxième appel: installation
        assert calls[1][0][0] == [
            str(Path("/path/to/environments/test_env/bin/pip")), 
            "install", 
            "flask"
        ]

    def test_install_packages_offline_mode(self, package_service: PackageService, mock_subprocess: MagicMock | AsyncMock) -> None:
        """Teste l'installation de packages en mode hors ligne."""
        # Mocker les dépendances
        package_service._get_environment_path = lambda name: Path("/path/to/environments/test_env")
        package_service.env_service.get_pip_executable.return_value = Path("/path/to/environments/test_env/bin/pip")
        
        # Activer le mode hors ligne
        package_service.offline_mode = True
        package_service.use_cache = True
        
        # Chemin fictif pour le fichier wheel
        wheel_path = Path("/path/to/cache/flask-2.0.1.whl")
        
        # Simuler que le package est dans le cache
        package_service.cache_service.has_package.return_value = True
        package_service.cache_service.get_package.return_value = wheel_path
        
        # Simuler un succès d'installation
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Successfully installed flask-2.0.1"
        
        # Patcher Path.exists et shutil.copy2 pour éviter les erreurs de fichier inexistant
        with patch('pathlib.Path.exists', return_value=True), \
             patch('shutil.copy2', return_value=None), \
             patch('os.path.getsize', return_value=1024), \
             patch('tempfile.TemporaryDirectory') as mock_temp_dir:
            
            # Configurer le mock du répertoire temporaire
            mock_temp_dir.return_value.__enter__.return_value = "/tmp/fake_temp_dir"
            
            # Installer un package
            success, message = package_service.install_packages("test_env", ["flask"])
    
            # Vérifier le résultat
            assert success is True
            assert "succès" in message
        
        # Vérifier que le cache a été utilisé
        package_service.cache_service.has_package.assert_called_with("flask", None)
        package_service.cache_service.get_package.assert_called_with("flask", None)
        
        # Vérifier que subprocess.run a été appelé avec le chemin du fichier wheel
        mock_subprocess.assert_called()
        # Note: Nous ne vérifions pas les détails exacts de l'appel car ils impliquent
        # un répertoire temporaire qui change à chaque exécution
    
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