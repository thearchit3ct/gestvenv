"""Tests pour le service EnvironmentService."""

import pytest
from unittest.mock import patch, MagicMock
import os
from pathlib import Path

from gestvenv.services.environment_service import EnvironmentService
from gestvenv.core.models import EnvironmentHealth

class TestEnvironmentService:
    """Tests pour le service EnvironmentService."""
    
    @pytest.fixture
    def env_service(self) -> EnvironmentService:
        """Fixture pour créer une instance du service."""
        return EnvironmentService()
    
    # def test_validate_environment_name(self, env_service) -> None:
    #     """Teste la validation des noms d'environnement."""
    #     # Noms valides
    #     valid, _ = env_service.validate_environment_name("valid_name")
    #     assert valid is True
        
    #     # Noms invalides
    #     valid, error = env_service.validate_environment_name("")
    #     assert valid is False
    #     assert "vide" in error
        
    #     valid, error = env_service.validate_environment_name("a" * 100)
    #     assert valid is False
    #     assert "long" in error
        
    #     valid, error = env_service.validate_environment_name("invalid@name")
    #     assert valid is False
    #     assert "caractères" in error
        
    #     valid, error = env_service.validate_environment_name("system")
    #     assert valid is False
    #     assert "réservé" in error
    
    def test_validate_python_version(self, env_service) -> None:
        """Teste la validation des versions Python."""
        # Versions valides
        valid, _ = env_service.validate_python_version("python")
        assert valid is True
        
        valid, _ = env_service.validate_python_version("python3")
        assert valid is True
        
        valid, _ = env_service.validate_python_version("python3.9")
        assert valid is True
        
        valid, _ = env_service.validate_python_version("3.9")
        assert valid is True
        
        # Versions invalides
        valid, error = env_service.validate_python_version("3.5")
        assert valid is False
        assert "3.6" in error
        
        valid, error = env_service.validate_python_version("invalid")
        assert valid is False
        assert "Format" in error
    
    def test_validate_packages_list(self, env_service) -> None:
        """Teste la validation des listes de packages."""
        # Liste valide
        valid, packages, _ = env_service.validate_packages_list("flask,pytest")
        assert valid is True
        assert len(packages) == 2
        assert "flask" in packages
        assert "pytest" in packages
        
        # Liste vide
        valid, _, error = env_service.validate_packages_list("")
        assert valid is False
        assert "vide" in error
        
        # Package invalide
        valid, _, error = env_service.validate_packages_list("flask,invalid package")
        assert valid is False
        assert "invalid package" in error
    
    # def test_resolve_path(self, env_service, monkeypatch) -> None:
    #     """Teste la résolution des chemins."""
    #     # Configurer le répertoire courant et utilisateur
    #     monkeypatch.setattr(Path, 'cwd', lambda: Path('/current/dir'))
    #     monkeypatch.setattr(Path, 'home', lambda: Path('/home/testuser'))
        
    #     # Chemin absolu
    #     path = env_service.resolve_path("/absolute/path")
    #     assert str(path) == "/absolute/path"
        
    #     # Chemin relatif
    #     path = env_service.resolve_path("relative/path")
    #     assert str(path) == "/current/dir/relative/path"
        
    #     # Chemin utilisateur
    #     path = env_service.resolve_path("~/user/path")
    #     assert str(path) == "/home/testuser/user/path"
    
    # def test_get_default_venv_dir(self, env_service, monkeypatch) -> None:
    #     """Teste la récupération du répertoire par défaut des environnements."""
    #     # Mocker get_app_data_dir pour retourner un chemin connu
    #     monkeypatch.setattr(
    #         env_service, 
    #         'get_app_data_dir', 
    #         lambda: Path('/app/data/dir')
    #     )
        
    #     venv_dir = env_service.get_default_venv_dir()
    #     assert str(venv_dir) == "/app/data/dir/environments"
    
    # def test_create_environment(self, env_service, temp_dir, mock_subprocess) -> None:
    #     """Teste la création d'un environnement virtuel."""
    #     # Mocker les dépendances
    #     env_service.get_default_venv_dir = lambda: temp_dir / "environments"
        
    #     # Simuler un succès de création
    #     mock_subprocess.return_value.returncode = 0
        
    #     env_path = temp_dir / "environments" / "test_env"
        
    #     # Créer l'environnement
    #     success, message = env_service.create_environment("test_env", "python3", env_path)
        
    #     # Vérifier le résultat
    #     assert success is True
    #     assert "succès" in message
        
    #     # Vérifier que subprocess.run a été appelé avec les bons arguments
    #     mock_subprocess.assert_called_once()
    #     args, _ = mock_subprocess.call_args
    #     assert "python3" in args[0]
    #     assert "venv" in args[0]
    #     assert str(env_path) in args[0]
        
    #     # Simuler un échec de création
    #     mock_subprocess.reset_mock()
    #     mock_subprocess.return_value.returncode = 1
    #     mock_subprocess.return_value.stderr = "Error creating environment"
        
    #     success, message = env_service.create_environment("fail_env", "python3", temp_dir / "environments" / "fail_env")
        
    #     assert success is False
    #     assert "Échec" in message or "Error" in message
    
    def test_check_environment_health(self, env_service, mock_env_path) -> None:
        """Teste la vérification de l'état de santé d'un environnement."""
        # Mocker les méthodes pour retourner des chemins existants
        env_service.get_python_executable = lambda name, path: mock_env_path / "bin" / "python"
        env_service.get_pip_executable = lambda name, path: mock_env_path / "bin" / "pip"
        env_service.get_activation_script_path = lambda name, path: mock_env_path / "bin" / "activate"
        
        # Vérifier la santé
        health = env_service.check_environment_health("test_env", mock_env_path)
        
        # Vérifier les résultats
        assert isinstance(health, EnvironmentHealth)
        assert health.exists is True
        assert health.python_available is True
        assert health.pip_available is True
        assert health.activation_script_exists is True
        
        # Tester avec un environnement inexistant
        nonexistent_path = mock_env_path.parent / "nonexistent"
        health = env_service.check_environment_health("nonexistent", nonexistent_path)
        
        assert health.exists is False
        assert health.python_available is False
        assert health.pip_available is False
        assert health.activation_script_exists is False