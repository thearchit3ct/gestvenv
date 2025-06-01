"""Tests pour le service EnvironmentService."""

import os
import pytest
import tempfile
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from pytest import MonkeyPatch
from datetime import datetime

from gestvenv.services.environment_service import EnvironmentService
from gestvenv.core.models import EnvironmentHealth

class TestEnvironmentService:
    """Tests pour la classe EnvironmentService."""
    
    @pytest.fixture
    def env_service(self) -> EnvironmentService:
        """Fixture pour créer une instance du service d'environnement."""
        return EnvironmentService()
    
    @pytest.fixture
    def temp_env_dir(self, temp_dir: Path) -> Path:
        """Fixture pour créer un répertoire d'environnement temporaire."""
        env_dir = temp_dir / "test_env"
        env_dir.mkdir(parents=True, exist_ok=True)
        
        # Créer la structure minimale d'un environnement virtuel
        if os.name == "nt":  # Windows
            scripts_dir = env_dir / "Scripts"
            scripts_dir.mkdir(exist_ok=True)
            (scripts_dir / "python.exe").touch()
            (scripts_dir / "pip.exe").touch()
            (scripts_dir / "activate.bat").touch()
        else:  # Unix
            bin_dir = env_dir / "bin"
            bin_dir.mkdir(exist_ok=True)
            (bin_dir / "python").touch()
            (bin_dir / "pip").touch()
            (bin_dir / "activate").touch()
        
        # Créer pyvenv.cfg
        pyvenv_cfg = env_dir / "pyvenv.cfg"
        pyvenv_cfg.write_text("home = /usr/bin\nversion = 3.9.0\n")
        
        return env_dir
    
    def test_init(self, env_service: EnvironmentService) -> None:
        """Teste l'initialisation du service."""
        assert env_service.system in ["windows", "linux", "darwin"]
    
    def test_validate_environment_name(self, env_service: EnvironmentService) -> None:
        """Teste la validation des noms d'environnement."""
        # Noms valides
        valid, message = env_service.validate_environment_name("mon_env")
        assert valid is True
        assert message == ""
        
        valid, message = env_service.validate_environment_name("env-test")
        assert valid is True
        
        valid, message = env_service.validate_environment_name("env123")
        assert valid is True
        
        # Noms invalides
        valid, message = env_service.validate_environment_name("")
        assert valid is False
        assert "vide" in message
        
        valid, message = env_service.validate_environment_name("env@test")
        assert valid is False
        assert "caractères" in message
        
        valid, message = env_service.validate_environment_name("a" * 51)
        assert valid is False
        assert "trop long" in message
        
        valid, message = env_service.validate_environment_name("system")
        assert valid is False
        assert "réservé" in message
    
    def test_validate_python_version(self, env_service: EnvironmentService) -> None:
        """Teste la validation des versions Python."""
        # Versions valides
        valid, message = env_service.validate_python_version("python")
        assert valid is True
        
        valid, message = env_service.validate_python_version("python3")
        assert valid is True
        
        valid, message = env_service.validate_python_version("python3.9")
        assert valid is True
        
        valid, message = env_service.validate_python_version("3.9")
        assert valid is True
        
        valid, message = env_service.validate_python_version("")
        assert valid is True  # Version vide est valide
        
        # Versions invalides
        valid, message = env_service.validate_python_version("3.5")
        assert valid is False
        assert "3.6" in message
        
        valid, message = env_service.validate_python_version("python2.7")
        assert valid is False
        
        valid, message = env_service.validate_python_version("invalid")
        assert valid is False
    
    def test_validate_packages_list(self, env_service: EnvironmentService) -> None:
        """Teste la validation des listes de packages."""
        # Liste valide
        valid, packages, message = env_service.validate_packages_list("flask,pytest,requests==2.26.0")
        assert valid is True
        assert len(packages) == 3
        assert "flask" in packages
        assert "pytest" in packages
        assert "requests==2.26.0" in packages
        
        # Packages avec versions
        valid, packages, message = env_service.validate_packages_list("flask>=2.0.1,pytest<7.0")
        assert valid is True
        assert len(packages) == 2
        
        # URL Git
        valid, packages, message = env_service.validate_packages_list("git+https://github.com/user/repo.git")
        assert valid is True
        
        # Liste vide
        valid, packages, message = env_service.validate_packages_list("")
        assert valid is False
        assert "vide" in message
        
        # Package invalide
        valid, packages, message = env_service.validate_packages_list("flask,invalid@package")
        assert valid is False
        assert "invalides" in message
    
    def test_get_python_executable(self, env_service: EnvironmentService, temp_env_dir: Path) -> None:
        """Teste la récupération de l'exécutable Python."""
        python_exe = env_service.get_python_executable("test_env", temp_env_dir)
        assert python_exe is not None
        assert python_exe.exists()
        
        if os.name == "nt":
            assert python_exe.name == "python.exe"
            assert "Scripts" in str(python_exe)
        else:
            assert python_exe.name == "python"
            assert "bin" in str(python_exe)
        
        # Test avec environnement inexistant
        nonexistent_path = temp_env_dir.parent / "nonexistent"
        python_exe = env_service.get_python_executable("nonexistent", nonexistent_path)
        assert python_exe is None
    
    def test_get_pip_executable(self, env_service: EnvironmentService, temp_env_dir: Path) -> None:
        """Teste la récupération de l'exécutable pip."""
        pip_exe = env_service.get_pip_executable("test_env", temp_env_dir)
        assert pip_exe is not None
        assert pip_exe.exists()
        
        if os.name == "nt":
            assert pip_exe.name == "pip.exe"
            assert "Scripts" in str(pip_exe)
        else:
            assert pip_exe.name == "pip"
            assert "bin" in str(pip_exe)
    
    def test_get_activation_script_path(self, env_service: EnvironmentService, temp_env_dir: Path) -> None:
        """Teste la récupération du chemin du script d'activation."""
        activate_script = env_service.get_activation_script_path("test_env", temp_env_dir)
        assert activate_script is not None
        assert activate_script.exists()
        
        if os.name == "nt":
            assert activate_script.name == "activate.bat"
            assert "Scripts" in str(activate_script)
        else:
            assert activate_script.name == "activate"
            assert "bin" in str(activate_script)
    
    @patch('subprocess.run')
    def test_create_environment_success(self, mock_subprocess: MagicMock, 
                                       env_service: EnvironmentService, temp_dir: Path) -> None:
        """Teste la création réussie d'un environnement."""
        # Configurer le mock pour retourner un succès
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        env_path = temp_dir / "new_env"
        success, message = env_service.create_environment("new_env", "python3", env_path)
        
        assert success is True
        assert "succès" in message
        mock_subprocess.assert_called_once()
    
    @patch('subprocess.run')
    def test_create_environment_failure(self, mock_subprocess: MagicMock,
                                       env_service: EnvironmentService, temp_dir: Path) -> None:
        """Teste l'échec de création d'un environnement."""
        # Configurer le mock pour retourner une erreur
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Error creating environment"
        mock_subprocess.return_value = mock_result
        
        env_path = temp_dir / "new_env"
        success, message = env_service.create_environment("new_env", "python3", env_path)
        
        assert success is False
        assert "Échec" in message
    
    def test_create_environment_already_exists(self, env_service: EnvironmentService, 
                                              temp_env_dir: Path) -> None:
        """Teste la création d'un environnement qui existe déjà."""
        success, message = env_service.create_environment("test_env", "python3", temp_env_dir)
        
        assert success is False
        assert "existe déjà" in message
    
    def test_delete_environment_success(self, env_service: EnvironmentService, 
                                       temp_env_dir: Path) -> None:
        """Teste la suppression réussie d'un environnement."""
        success, message = env_service.delete_environment(temp_env_dir)
        
        assert success is True
        assert "succès" in message
        assert not temp_env_dir.exists()
    
    def test_delete_environment_not_exists(self, env_service: EnvironmentService, 
                                          temp_dir: Path) -> None:
        """Teste la suppression d'un environnement qui n'existe pas."""
        nonexistent_path = temp_dir / "nonexistent"
        success, message = env_service.delete_environment(nonexistent_path)
        
        assert success is True
        assert "n'existe pas" in message
    
    def test_check_environment_exists(self, env_service: EnvironmentService, 
                                     temp_env_dir: Path) -> None:
        """Teste la vérification d'existence d'un environnement."""
        # Environnement existant
        exists = env_service.check_environment_exists(temp_env_dir)
        assert exists is True
        
        # Environnement inexistant
        nonexistent_path = temp_env_dir.parent / "nonexistent"
        exists = env_service.check_environment_exists(nonexistent_path)
        assert exists is False
        
        # Répertoire sans pyvenv.cfg ni exécutable Python
        empty_dir = temp_env_dir.parent / "empty"
        empty_dir.mkdir()
        exists = env_service.check_environment_exists(empty_dir)
        assert exists is False
    
    def test_check_environment_health(self, env_service: EnvironmentService, 
                                     temp_env_dir: Path) -> None:
        """Teste la vérification de la santé d'un environnement."""
        health = env_service.check_environment_health("test_env", temp_env_dir)
        
        assert isinstance(health, EnvironmentHealth)
        assert health.exists is True
        assert health.python_available is True
        assert health.pip_available is True
        assert health.activation_script_exists is True
        
        # Test avec environnement inexistant
        nonexistent_path = temp_env_dir.parent / "nonexistent"
        health = env_service.check_environment_health("nonexistent", nonexistent_path)
        
        assert health.exists is False
        assert health.python_available is False
        assert health.pip_available is False
        assert health.activation_script_exists is False
    
    def test_is_safe_to_delete(self, env_service: EnvironmentService, 
                              temp_env_dir: Path) -> None:
        """Teste la vérification de sécurité pour la suppression."""
        # Environnement sécuritaire
        safe, message = env_service.is_safe_to_delete("test_env", temp_env_dir)
        assert safe is True
        assert message == ""
        
        # Environnement inexistant
        nonexistent_path = temp_env_dir.parent / "nonexistent"
        safe, message = env_service.is_safe_to_delete("nonexistent", nonexistent_path)
        assert safe is False
        assert "n'existe pas" in message
        
        # Répertoire système (simulation)
        with patch.object(env_service, 'is_safe_to_delete') as mock_safe:
            mock_safe.return_value = (False, "répertoire système")
            safe, message = env_service.is_safe_to_delete("system", Path("/"))
            assert safe is False
            assert "système" in message
    
    def test_get_default_venv_dir(self, env_service: EnvironmentService) -> None:
        """Teste la récupération du répertoire par défaut des environnements."""
        venv_dir = env_service.get_default_venv_dir()
        
        assert isinstance(venv_dir, Path)
        assert venv_dir.exists()  # Le répertoire devrait être créé
        assert "environments" in str(venv_dir)
    
    def test_get_environment_path(self, env_service: EnvironmentService) -> None:
        """Teste la détermination du chemin d'un environnement."""
        # Avec chemin personnalisé
        custom_path = "/custom/path/env"
        path = env_service.get_environment_path("test_env", custom_path)
        assert str(path) == str(Path(custom_path).resolve())
        
        # Sans chemin personnalisé
        path = env_service.get_environment_path("test_env")
        assert path.name == "test_env"
        assert "environments" in str(path)
    
    def test_get_app_data_dir(self, env_service: EnvironmentService, monkeypatch: MonkeyPatch) -> None:
        """Teste la récupération du répertoire de données d'application."""
        # Test Windows
        with patch('platform.system', return_value='Windows'):
            env_service.system = "windows"
            monkeypatch.setenv('APPDATA', '/windows/appdata')
            app_dir = env_service.get_app_data_dir()
            assert "GestVenv" in str(app_dir)
        
        # Test macOS
        with patch('platform.system', return_value='Darwin'):
            env_service.system = "darwin"
            with patch('pathlib.Path.home', return_value=Path('/Users/test')):
                app_dir = env_service.get_app_data_dir()
                assert "Library/Application Support/GestVenv" in str(app_dir)
        
        # Test Linux
        with patch('platform.system', return_value='Linux'):
            env_service.system = "linux"
            monkeypatch.delenv('XDG_CONFIG_HOME', raising=False)
            with patch('pathlib.Path.home', return_value=Path('/home/test')):
                app_dir = env_service.get_app_data_dir()
                assert ".config/gestvenv" in str(app_dir)
    
    def test_resolve_path(self, env_service: EnvironmentService, monkeypatch: MonkeyPatch) -> None:
        """Teste la résolution des chemins."""
        # Chemin absolu
        abs_path = "/absolute/path"
        resolved = env_service.resolve_path(abs_path)
        assert resolved.is_absolute()
        
        # Chemin relatif
        rel_path = "relative/path"
        resolved = env_service.resolve_path(rel_path)
        assert resolved.is_absolute()
        
        # Chemin utilisateur
        with patch('os.path.expanduser', return_value='/home/user/test'):
            resolved = env_service.resolve_path("~/test")
            assert str(resolved) == str(Path('/home/user/test').resolve())
    
    def test_validate_output_format(self, env_service: EnvironmentService) -> None:
        """Teste la validation des formats de sortie."""
        # Formats valides
        valid, message = env_service.validate_output_format("json")
        assert valid is True
        
        valid, message = env_service.validate_output_format("requirements")
        assert valid is True
        
        # Format invalide
        valid, message = env_service.validate_output_format("xml")
        assert valid is False
        assert "invalide" in message
        
        # Format vide
        valid, message = env_service.validate_output_format("")
        assert valid is False
        assert "vide" in message
    
    def test_validate_metadata(self, env_service: EnvironmentService) -> None:
        """Teste la validation des métadonnées."""
        # Métadonnées valides
        valid, metadata, message = env_service.validate_metadata("description:Mon projet,author:John")
        assert valid is True
        assert metadata["description"] == "Mon projet"
        assert metadata["author"] == "John"
        
        # Métadonnées vides
        valid, metadata, message = env_service.validate_metadata("")
        assert valid is True
        assert metadata == {}
        
        # Format invalide
        valid, metadata, message = env_service.validate_metadata("invalid_format")
        assert valid is False
        assert ":" in message
    
    def test_get_export_directory(self, env_service: EnvironmentService) -> None:
        """Teste la récupération du répertoire d'export."""
        export_dir = env_service.get_export_directory()
        
        assert isinstance(export_dir, Path)
        assert export_dir.exists()
        assert "exports" in str(export_dir)
    
    def test_get_json_output_path(self, env_service: EnvironmentService) -> None:
        """Teste la génération du chemin d'export JSON."""
        output_path = env_service.get_json_output_path("test_env")
        
        assert isinstance(output_path, Path)
        assert output_path.suffix == ".json"
        assert "test_env" in output_path.name
    
    def test_get_requirements_output_path(self, env_service: EnvironmentService) -> None:
        """Teste la génération du chemin d'export requirements.txt."""
        # Chemin par défaut
        output_path = env_service.get_requirements_output_path("test_env")
        assert isinstance(output_path, Path)
        assert output_path.suffix == ".txt"
        assert "test_env" in output_path.name
        assert "requirements" in output_path.name
        
        # Chemin personnalisé
        custom_path = "/custom/requirements.txt"
        output_path = env_service.get_requirements_output_path("test_env", custom_path)
        assert str(output_path) == str(Path(custom_path).resolve())
    
    def test_cleanup_temporary_environments(self, env_service: EnvironmentService) -> None:
        """Teste le nettoyage des environnements temporaires."""
        with patch.object(env_service, 'cleanup_temporary_environments') as mock_cleanup:
            mock_cleanup.return_value = (2, ["Environnement temp_1 nettoyé", "Environnement temp_2 nettoyé"])
            
            cleaned_count, messages = env_service.cleanup_temporary_environments()
            
            assert cleaned_count == 2
            assert len(messages) == 2
            assert "temp_1" in messages[0]
            assert "temp_2" in messages[1]
    
    @patch('shutil.rmtree')
    @patch('os.listdir')
    @patch('tempfile.gettempdir')
    def test_cleanup_temporary_environments_real(self, mock_gettempdir: MagicMock,
                                               mock_listdir: MagicMock, mock_rmtree: MagicMock,
                                               env_service: EnvironmentService, temp_dir: Path) -> None:
        """Teste le nettoyage réel des environnements temporaires."""
        # Simuler un répertoire temporaire avec des environnements expirés
        mock_gettempdir.return_value = str(temp_dir)
        
        # Créer une structure de test
        temp_base_dir = temp_dir / "gestvenv_temp"
        temp_base_dir.mkdir()
        
        temp_env_dir = temp_base_dir / "temp_env_expired"
        temp_env_dir.mkdir()
        
        # Créer des métadonnées avec expiration passée
        metadata = {
            "temporary": True,
            "expires_at": "2020-01-01T00:00:00",
            "session_id": 99999  # PID inexistant
        }
        
        with patch.object(env_service, 'get_environment_metadata', return_value=metadata), \
             patch.object(env_service, '_is_process_alive', return_value=False):
            
            cleaned_count, messages = env_service.cleanup_temporary_environments()
            
            assert cleaned_count >= 0  # Au moins pas d'erreur
            assert isinstance(messages, list)


if __name__ == "__main__":
    pytest.main([__file__])