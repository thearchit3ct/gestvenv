"""Tests pour la classe EnvironmentManager."""

from typing import Any, Generator
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import datetime

from gestvenv.core.env_manager import EnvironmentManager
from gestvenv.core.models import EnvironmentInfo, PackageInfo, EnvironmentHealth

class TestEnvironmentManager:
    """Tests pour la classe EnvironmentManager."""
    
    @pytest.fixture
    def env_manager(self, temp_config_file: Any) -> Generator[EnvironmentManager, Any, None]:
        """Fixture pour créer une instance du gestionnaire d'environnements."""
        with patch('gestvenv.core.env_manager.ConfigManager') as mock_config_manager, \
             patch('gestvenv.services.environment_service.EnvironmentService') as mock_env_service, \
             patch('gestvenv.services.package_service.PackageService') as mock_pkg_service, \
             patch('gestvenv.services.system_service.SystemService') as mock_sys_service:
            
            # Configurer les mocks
            mock_config_manager.return_value.config_path = temp_config_file
            
            manager = EnvironmentManager(config_path=temp_config_file)
            
            # Remplacer les services par des mocks
            manager.env_service = mock_env_service()
            manager.pkg_service = mock_pkg_service()
            manager.sys_service = mock_sys_service()
            manager.config_manager = mock_config_manager()
            
            yield manager
    
    def test_create_environment(self, env_manager: EnvironmentManager) -> None:
        """Teste la création d'un environnement virtuel."""
        # Configurer les mocks pour un succès
        env_manager.env_service.validate_environment_name.return_value = (True, "")
        env_manager.env_service.validate_python_version.return_value = (True, "")
        env_manager.env_service.validate_packages_list.return_value = (True, ["flask", "pytest"], "")
        env_manager.env_service.get_environment_path.return_value = Path("/path/to/environments/test_env")
        env_manager.env_service.create_environment.return_value = (True, "Environnement créé avec succès")
        env_manager.config_manager.environment_exists.return_value = False
        env_manager.sys_service.check_python_version.return_value = "3.9.0"
        env_manager.config_manager.add_environment.return_value = True
        env_manager.config_manager.get_all_environments.return_value = {"test_env": "mock"}

        # Mock les services de packages si des packages sont spécifiés
        env_manager.pkg_service.install_packages.return_value = (True, "Packages installés")
        env_manager.env_service.check_environment_health.return_value = EnvironmentHealth()

        # Créer un environnement
        success, message = env_manager.create_environment(
            "test_env",
            python_version="python3.9",
            packages="flask,pytest"
        )

        # Vérifier le résultat
        assert success is True
        assert "succès" in message

        # Vérifier que les méthodes ont été appelées correctement
        env_manager.env_service.validate_environment_name.assert_called_once_with("test_env")
        env_manager.env_service.validate_python_version.assert_called_once_with("python3.9")
        env_manager.env_service.create_environment.assert_called_once()
        env_manager.config_manager.add_environment.assert_called_once()
    
    def test_activate_environment(self, env_manager: EnvironmentManager) -> None:
        """Teste l'activation d'un environnement virtuel."""
        # Configurer les mocks pour un succès
        env_manager.config_manager.environment_exists.return_value = True
        env_manager.config_manager.get_environment.return_value = EnvironmentInfo(
            name="test_env",
            path=Path("/path/to/environments/test_env"),
            python_version="3.9.0"
        )
        env_manager.env_service.check_environment_exists.return_value = True
        env_manager.sys_service.get_activation_command.return_value = "source /path/to/environments/test_env/bin/activate"
        
        # Activer un environnement
        success, message = env_manager.activate_environment("test_env")
        
        # Vérifier le résultat
        assert success is True
        assert "source" in message
        
        # Vérifier que les méthodes ont été appelées correctement
        env_manager.config_manager.environment_exists.assert_called_once_with("test_env")
        env_manager.config_manager.get_environment.assert_called_once_with("test_env")
        env_manager.env_service.check_environment_exists.assert_called_once()
        env_manager.sys_service.get_activation_command.assert_called_once()
        env_manager.config_manager.set_active_environment.assert_called_once_with("test_env")
        
        # Configurer les mocks pour un échec
        env_manager.config_manager.environment_exists.return_value = False
        
        # Essayer d'activer un environnement inexistant
        success, message = env_manager.activate_environment("nonexistent")
        
        assert success is False
        assert "n'existe pas" in message
    
    def test_deactivate_environment(self, env_manager: EnvironmentManager) -> None:
        """Teste la désactivation de l'environnement actif."""
        # Configurer les mocks
        env_manager.config_manager.get_active_environment.return_value = "test_env"
        
        # Désactiver l'environnement
        success, message = env_manager.deactivate_environment()
        
        # Vérifier le résultat
        assert success is True
        assert "deactivate" in message
        
        # Vérifier que les méthodes ont été appelées correctement
        env_manager.config_manager.clear_active_environment.assert_called_once()
        
        # Cas où aucun environnement n'est actif
        env_manager.config_manager.get_active_environment.return_value = None
        
        success, message = env_manager.deactivate_environment()
        
        assert success is False
        assert "Aucun environnement actif" in message
    
    def test_delete_environment(self, env_manager: EnvironmentManager) -> None:
        """Teste la suppression d'un environnement virtuel."""
        # Configurer les mocks pour un succès
        env_manager.config_manager.environment_exists.return_value = True
        env_manager.config_manager.get_environment.return_value = EnvironmentInfo(
            name="test_env",
            path=Path("/path/to/environments/test_env"),
            python_version="3.9.0"
        )
        env_manager.env_service.is_safe_to_delete.return_value = (True, "")
        env_manager.env_service.delete_environment.return_value = (True, "Environnement supprimé avec succès")
        
        # Supprimer un environnement
        success, message = env_manager.delete_environment("test_env")
        
        # Vérifier le résultat
        assert success is True
        assert "succès" in message
        
        # Vérifier que les méthodes ont été appelées correctement
        env_manager.config_manager.environment_exists.assert_called_once_with("test_env")
        env_manager.config_manager.get_environment.assert_called_once_with("test_env")
        env_manager.env_service.is_safe_to_delete.assert_called_once()
        env_manager.env_service.delete_environment.assert_called_once()
        env_manager.config_manager.remove_environment.assert_called_once_with("test_env")
        
        # Configurer les mocks pour un échec
        env_manager.config_manager.environment_exists.return_value = False
        
        # Essayer de supprimer un environnement inexistant
        success, message = env_manager.delete_environment("nonexistent")
        
        assert success is False
        assert "n'existe pas" in message
    
    def test_list_environments(self, env_manager: EnvironmentManager) -> None:
        """Teste la récupération de la liste des environnements."""
        # Configurer les mocks
        env_manager.config_manager.get_all_environments.return_value = {
            "test_env": EnvironmentInfo(
                name="test_env",
                path=Path("/path/to/environments/test_env"),
                python_version="3.9.0"
            ),
            "dev_env": EnvironmentInfo(
                name="dev_env",
                path=Path("/path/to/environments/dev_env"),
                python_version="3.10.0"
            )
        }
        env_manager.config_manager.get_active_environment.return_value = "test_env"
        env_manager.env_service.check_environment_exists.return_value = True
        env_manager.env_service.check_environment_health.return_value = EnvironmentHealth(
            exists=True,
            python_available=True,
            pip_available=True,
            activation_script_exists=True
        )
        
        # Récupérer la liste des environnements
        environments = env_manager.list_environments()
        
        # Vérifier le résultat
        assert len(environments) == 2
        assert environments[0]["name"] == "test_env"
        assert environments[0]["active"] is True
        assert environments[0]["exists"] is True
        assert environments[1]["name"] == "dev_env"
        assert environments[1]["active"] is False
        
        # Vérifier que les méthodes ont été appelées correctement
        env_manager.config_manager.get_all_environments.assert_called_once()
        env_manager.config_manager.get_active_environment.assert_called_once()
        assert env_manager.env_service.check_environment_exists.call_count == 2
        assert env_manager.env_service.check_environment_health.call_count == 2
    
    def test_get_environment_info(self, env_manager: EnvironmentManager, mock_package_list: list[dict[str, str]]) -> None:
        """Teste la récupération des informations d'un environnement."""
        # Configurer les mocks
        env_manager.config_manager.environment_exists.return_value = True
        env_manager.config_manager.get_environment.return_value = EnvironmentInfo(
            name="test_env",
            path=Path("/path/to/environments/test_env"),
            python_version="3.9.0",
            packages=["flask", "pytest"]
        )
        env_manager.config_manager.get_active_environment.return_value = "test_env"
        env_manager.env_service.check_environment_exists.return_value = True
        env_manager.env_service.check_environment_health.return_value = EnvironmentHealth(
            exists=True,
            python_available=True,
            pip_available=True,
            activation_script_exists=True
        )
        env_manager.env_service.get_python_executable.return_value = Path("/path/to/environments/test_env/bin/python")
        env_manager.env_service.get_pip_executable.return_value = Path("/path/to/environments/test_env/bin/pip")
        env_manager.env_service.get_activation_script_path.return_value = Path("/path/to/environments/test_env/bin/activate")
        env_manager.pkg_service.list_installed_packages.return_value = mock_package_list
        
        # Récupérer les informations de l'environnement
        env_info = env_manager.get_environment_info("test_env")
        
        # Vérifier le résultat
        assert env_info is not None
        assert env_info["name"] == "test_env"
        assert env_info["python_version"] == "3.9.0"
        assert env_info["active"] is True
        assert env_info["exists"] is True
        assert env_info["health"]["exists"] is True
        assert env_info["health"]["python_available"] is True
        assert len(env_info["packages_installed"]) == 3
        assert env_info["packages_installed"][0]["name"] == "pytest"
        assert env_info["packages_installed"][1]["name"] == "flask"
        
        # Vérifier que les méthodes ont été appelées correctement
        env_manager.config_manager.environment_exists.assert_called_once_with("test_env")
        env_manager.config_manager.get_environment.assert_called_once_with("test_env")
        env_manager.env_service.check_environment_exists.assert_called_once()
        env_manager.env_service.check_environment_health.assert_called_once()
        env_manager.pkg_service.list_installed_packages.assert_called_once_with("test_env")
        
        # Configurer les mocks pour un environnement inexistant
        env_manager.config_manager.environment_exists.return_value = False
        
        # Essayer de récupérer les informations d'un environnement inexistant
        env_info = env_manager.get_environment_info("nonexistent")
        
        assert env_info is None
    
    # def test_clone_environment(self, env_manager: EnvironmentManager) -> None:
    #     """Teste le clonage d'un environnement existant."""
    #     # Configurer les mocks pour un succès
    #     env_manager.config_manager.environment_exists.side_effect = lambda name: name == "source_env"
    #     env_manager.env_service.validate_environment_name.return_value = (True, "")
        
    #     # Mock get_environment au lieu de get_environment_info
    #     source_env_info = EnvironmentInfo(
    #         name="source_env",
    #         path=Path("/path/to/environments/source_env"),
    #         python_version="3.9.0",
    #         packages=["flask==2.0.1", "pytest==6.2.5"]
    #     )
    #     env_manager.config_manager.get_environment.return_value = source_env_info
        
    #     # Mock create_environment directement sur l'instance
    #     with patch.object(env_manager, 'create_environment', return_value=(True, "Environnement créé avec succès")) as mock_create:
    #         # Mock pkg_service pour l'installation des packages
    #         env_manager.pkg_service.install_packages.return_value = (True, "Packages installés")
            
    #         # Cloner un environnement
    #         success, message = env_manager.clone_environment("source_env", "target_env")
            
    #         # Vérifier le résultat
    #         assert success is True
    #         assert "succès" in message
            
    #         # Vérifier les appels
    #         mock_create.assert_called_once_with("target_env", python_version="3.9.0")
    
    def test_update_packages(self, env_manager: EnvironmentManager) -> None:
        """Teste la mise à jour des packages d'un environnement."""
        # Configurer les mocks pour un succès
        env_manager.config_manager.environment_exists.return_value = True
        env_manager.config_manager.get_environment.return_value = EnvironmentInfo(
            name="test_env",
            path=Path("/path/to/environments/test_env"),
            python_version="3.9.0",
            packages=["flask==2.0.1", "pytest==6.2.5"]
        )
        env_manager.env_service.check_environment_exists.return_value = True
        env_manager.env_service.validate_packages_list.return_value = (True, ["flask"], "")
        env_manager.pkg_service.update_packages.return_value = (True, "Packages mis à jour avec succès")
        env_manager.pkg_service.list_installed_packages.return_value = [
            {"name": "flask", "version": "2.1.0"},
            {"name": "pytest", "version": "6.2.5"}
        ]
        
        # Mettre à jour des packages spécifiques
        success, message = env_manager.update_packages("test_env", packages="flask")
        
        # Vérifier le résultat
        assert success is True
        assert "succès" in message
        
        # Vérifier que les méthodes ont été appelées correctement
        env_manager.config_manager.environment_exists.assert_called_once_with("test_env")
        env_manager.config_manager.get_environment.assert_called_once_with("test_env")
        env_manager.env_service.check_environment_exists.assert_called_once()
        env_manager.env_service.validate_packages_list.assert_called_once_with("flask")
        env_manager.pkg_service.update_packages.assert_called_once()
        
        # Mettre à jour tous les packages
        env_manager.config_manager.environment_exists.reset_mock()
        env_manager.config_manager.get_environment.reset_mock()
        env_manager.env_service.check_environment_exists.reset_mock()
        env_manager.pkg_service.update_packages.reset_mock()
        
        success, message = env_manager.update_packages("test_env", all_packages=True)
        
        assert success is True
        assert "succès" in message
        
        # Vérifier que les méthodes ont été appelées correctement
        env_manager.config_manager.environment_exists.assert_called_once_with("test_env")
        env_manager.pkg_service.update_packages.assert_called_once()
        
        # Configurer les mocks pour un échec
        env_manager.config_manager.environment_exists.return_value = False
        
        # Essayer de mettre à jour les packages d'un environnement inexistant
        success, message = env_manager.update_packages("nonexistent")
        
        assert success is False
        assert "n'existe pas" in message
    
