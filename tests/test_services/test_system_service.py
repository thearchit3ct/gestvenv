"""Tests pour le service SystemService."""

from typing import Any, Generator
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import platform
from pathlib import Path

from gestvenv.services.system_service import SystemService

class TestSystemService:
    """Tests pour le service SystemService."""
    
    @pytest.fixture
    def system_service(self) -> Generator[SystemService, Any, None]:
        """Fixture pour créer une instance du service."""
        # Mocker les dépendances
        with patch('gestvenv.services.system_service.EnvironmentService') as mock_env_service:
            service = SystemService()
            service.env_service = mock_env_service()
            yield service
    
    def test_run_command(self, system_service: SystemService, mock_subprocess: MagicMock | AsyncMock) -> None:
        """Teste l'exécution de commandes."""
        # Simuler un succès
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Command output"
        mock_subprocess.return_value.stderr = ""
        
        # Exécuter une commande
        result = system_service.run_command(["echo", "test"])
        
        # Vérifier le résultat
        assert result['returncode'] == 0
        assert result['stdout'] == "Command output"
        assert result['stderr'] == ""
        
        # Vérifier que subprocess.run a été appelé correctement
        mock_subprocess.assert_called_once()
        args, kwargs = mock_subprocess.call_args
        assert args[0] == ["echo", "test"]
        
        # Simuler une erreur
        mock_subprocess.reset_mock()
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stderr = "Command failed"
        
        result = system_service.run_command(["invalid", "command"])
        
        assert result['returncode'] == 1
        assert result['stderr'] == "Command failed"
    
    def test_get_activation_command(self, system_service: SystemService, monkeypatch: pytest.MonkeyPatch) -> None:
        """Teste la récupération de la commande d'activation."""
        # Configurer le chemin du script d'activation
        activation_script = Path("/path/to/environments/test_env/bin/activate")
        system_service.env_service.get_activation_script_path.return_value = activation_script
        
        # Tester sous Unix
        monkeypatch.setattr(system_service, 'system', 'linux')
        cmd = system_service.get_activation_command("test_env", Path("/path/to/environments/test_env"))
        assert f'source "{activation_script}"' == cmd
        
        # Tester sous Windows
        monkeypatch.setattr(system_service, 'system', 'windows')
        cmd = system_service.get_activation_command("test_env", Path("/path/to/environments/test_env"))
        assert f'"{activation_script}"' == cmd
        
        # Script d'activation non trouvé
        system_service.env_service.get_activation_script_path.return_value = None
        cmd = system_service.get_activation_command("test_env", Path("/path/to/environments/test_env"))
        assert cmd is None
    
    def test_run_in_environment(self, system_service: SystemService, mock_subprocess: MagicMock | AsyncMock) -> None:
        """Teste l'exécution de commandes dans un environnement."""
        # Configurer le chemin de l'exécutable Python
        python_exe = Path("/path/to/environments/test_env/bin/python")
        system_service.env_service.get_python_executable.return_value = python_exe
        
        # Simuler un succès
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Script output"
        mock_subprocess.return_value.stderr = ""
        
        # Exécuter une commande
        ret_code, stdout, stderr = system_service.run_in_environment(
            "test_env", 
            Path("/path/to/environments/test_env"), 
            ["script.py", "--arg"]
        )
        
        # Vérifier le résultat
        assert ret_code == 0
        assert stdout == "Script output"
        assert stderr == ""
        
        # Vérifier que subprocess.run a été appelé correctement
        mock_subprocess.assert_called_once()
        args, _ = mock_subprocess.call_args
        assert str(python_exe) in str(args[0][0])
        assert "script.py" in args[0]
        assert "--arg" in args[0]
        
        # Exécutable Python non trouvé
        system_service.env_service.get_python_executable.return_value = None
        ret_code, stdout, stderr = system_service.run_in_environment(
            "test_env", 
            Path("/path/to/environments/test_env"), 
            ["script.py"]
        )
        
        assert ret_code == 1
        assert "introuvable" in stderr or "Environnement" in stderr
    
    def test_check_python_version(self, system_service: SystemService, mock_subprocess: MagicMock | AsyncMock) -> None:
        """Teste la vérification de la version Python."""
        # Simuler un succès
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Python 3.9.0"
        
        # Vérifier la version
        version = system_service.check_python_version("python3")
        
        # Vérifier le résultat
        assert version == "3.9.0"
        
        # Vérifier que subprocess.run a été appelé correctement
        mock_subprocess.assert_called_once()
        args, _ = mock_subprocess.call_args
        assert "python3" in args[0]
        assert "--version" in args[0]
        
        # Commande Python non disponible
        mock_subprocess.reset_mock()
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stderr = "Command not found"
        
        version = system_service.check_python_version("python3.99")
        assert version is None