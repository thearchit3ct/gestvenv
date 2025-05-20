"""Tests pour le module utils.system_utils."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pytest import MonkeyPatch
import platform
import os

from gestvenv.utils.system_utils import (
    run_simple_command, get_current_username, is_command_available,
    get_terminal_size, get_python_version_info
)

class TestSystemUtils:
    """Tests pour les fonctions utilitaires système."""
    
    def test_run_simple_command(self, mock_subprocess: MagicMock | AsyncMock) -> None:
        """Teste l'exécution de commandes simples."""
        # Configurer le mock pour retourner un résultat réussi
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Command output"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        # Exécuter une commande
        result = run_simple_command(["echo", "test"])
        
        # Vérifier que subprocess.run a été appelé correctement
        mock_subprocess.assert_called_once()
        args, kwargs = mock_subprocess.call_args
        assert args[0] == ["echo", "test"]
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        
        # Vérifier le résultat
        assert result["returncode"] == 0
        assert result["stdout"] == "Command output"
        assert result["stderr"] == ""
        
        # Tester avec une erreur
        mock_result.returncode = 1
        mock_result.stderr = "Error message"
        mock_subprocess.return_value = mock_result
        
        result = run_simple_command(["invalid", "command"])
        assert result["returncode"] == 1
        assert "Error message" in result["stderr"]
    
    def test_get_current_username(self, monkeypatch: MonkeyPatch) -> None:
        """Teste la récupération du nom d'utilisateur courant."""
        # Simuler différentes méthodes de récupération du nom d'utilisateur
        with patch('getpass.getuser', return_value="test_user"):
            username = get_current_username()
            assert username == "test_user"
        
        # Simuler un cas où getpass échoue
        with patch('getpass.getuser', side_effect=ImportError):
            # Configurer les variables d'environnement
            monkeypatch.setenv('USER', 'env_user')
            username = get_current_username()
            assert username == "env_user"
            
            # Tester avec USERNAME (Windows)
            monkeypatch.delenv('USER')
            monkeypatch.setenv('USERNAME', 'windows_user')
            username = get_current_username()
            assert username == "windows_user"
            
            # Tester le fallback par défaut
            monkeypatch.delenv('USERNAME')
            username = get_current_username()
            assert username == "unknown"
    
    def test_is_command_available(self, mock_subprocess: MagicMock | AsyncMock) -> None:
        """Teste la vérification de disponibilité des commandes."""
        # Commande disponible
        mock_subprocess.return_value.returncode = 0
        assert is_command_available("python") is True
        
        # Commande non disponible
        mock_subprocess.return_value.returncode = 1
        assert is_command_available("nonexistent_command") is False
    
    def test_get_terminal_size(self, monkeypatch: MonkeyPatch) -> None:
        """Teste la récupération de la taille du terminal."""
        with patch('shutil.get_terminal_size', return_value=(80, 24)):
            size = get_terminal_size()
            assert size == (80, 24)
        
        # Simuler une erreur
        with patch('shutil.get_terminal_size', side_effect=Exception):
            size = get_terminal_size()
            assert size == (80, 24)  # Valeurs par défaut
    
    def test_get_python_version_info(self) -> None:
        """Teste la récupération des informations de version Python."""
        info = get_python_version_info()
        
        # Vérifier les clés attendues
        assert "version" in info
        assert "implementation" in info
        assert "build" in info
        assert "compiler" in info
        assert "is_64bit" in info
        
        # Vérifier que la version correspond à celle de Python en cours d'exécution
        assert info["version"] == platform.python_version()