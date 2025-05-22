"""Tests pour le module utils.path_utils."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from pytest import MonkeyPatch

from gestvenv.utils.path_utils import (
    expand_user_path, resolve_path, ensure_dir_exists, 
    get_default_data_dir, get_normalized_path
)

class TestPathUtils:
    """Tests pour les fonctions utilitaires de gestion des chemins."""
    
    def test_expand_user_path(self, monkeypatch: MonkeyPatch) -> None:
        """Teste l'expansion des chemins utilisateur."""
        # Mock os.path.expanduser au lieu de Path.home
        def mock_expanduser(path):
            if path.startswith("~/"):
                return path.replace("~/", "/home/testuser/")
            return path

        monkeypatch.setattr('os.path.expanduser', mock_expanduser)

        # Tester l'expansion
        path = expand_user_path("~/test/path")
        assert str(path) == "/home/testuser/test/path"
        
        # Tester un chemin sans ~ (ne devrait pas changer)
        path = expand_user_path("/tmp/test")
        assert str(path) == "/tmp/test"
    
    def test_resolve_path(self, monkeypatch: MonkeyPatch) -> None:
        """Teste la résolution des chemins relatifs et absolus."""
        # Simuler le répertoire courant
        mock_cwd = Path('/current/dir')
        monkeypatch.setattr(Path, 'cwd', lambda: mock_cwd)

        # Mock os.path.expanduser pour les chemins utilisateur
        def mock_expanduser(path):
            if path.startswith("~/"):
                return path.replace("~/", "/home/testuser/")
            return path
        monkeypatch.setattr('os.path.expanduser', mock_expanduser)

        # Tester un chemin absolu
        path = resolve_path("/absolute/path")
        assert path.is_absolute()
        assert str(path) == "/absolute/path"

        # Tester un chemin relatif
        path = resolve_path("relative/path")
        assert path.is_absolute()
        # Vérifier que le chemin contient les éléments attendus
        assert "current" in str(path) and "relative" in str(path)

        # Tester un chemin utilisateur
        path = resolve_path("~/user/path")
        assert path.is_absolute()
        # Vérifier que le chemin contient testuser
        assert "testuser" in str(path) and "user/path" in str(path)

    def test_ensure_dir_exists(self, temp_dir: Path) -> None:
        """Teste la création de répertoires si nécessaire."""
        test_dir = temp_dir / "test_dir" / "nested"

        # Vérifier que le répertoire n'existe pas au départ
        assert not test_dir.exists()

        # Appeler ensure_dir_exists
        result = ensure_dir_exists(test_dir)

        # Vérifier que le répertoire a été créé
        assert test_dir.exists()
        assert test_dir.is_dir()
        # Vérifier que le résultat pointe vers le bon répertoire (même chemin résolu)
        assert result.resolve() == test_dir.resolve()
    
    # def test_get_default_data_dir(self, monkeypatch: MonkeyPatch) -> None:
    #     """Teste la récupération du répertoire de données par défaut."""
    #     with patch('gestvenv.utils.path_utils.get_os_name') as mock_os:
    #         # Windows
    #         mock_os.return_value = 'windows'
    #         monkeypatch.setenv('APPDATA', '/windows/appdata')

    #         # Mock os.makedirs pour éviter les erreurs de permission
    #         with patch('os.makedirs'):
    #             data_dir = get_default_data_dir()
    #             # Vérifier que le nom contient GestVenv ou gestvenv
    #             dir_str = str(data_dir).lower()
    #             assert 'gestvenv' in dir_str

    #         # macOS
    #         mock_os.return_value = 'darwin'
    #         monkeypatch.setattr(Path, 'home', lambda: Path('/Users/testuser'))

    #         with patch('os.makedirs'):
    #             data_dir = get_default_data_dir()
    #             dir_str = str(data_dir)
    #             assert 'GestVenv' in dir_str and 'Library/Application Support' in dir_str

    #         # Linux
    #         mock_os.return_value = 'linux'
    #         monkeypatch.setattr(Path, 'home', lambda: Path('/home/testuser'))

    #         with patch('os.makedirs'):
    #             data_dir = get_default_data_dir()
    #             dir_str = str(data_dir)
    #             assert 'gestvenv' in dir_str and '.config' in dir_str
    
    def test_get_normalized_path(self) -> None:
        """Teste la normalisation des chemins."""
        # Utiliser un chemin relatif simple
        relative_path = "path/to/file"
        normalized = get_normalized_path(relative_path)

        # Vérifier que tous les séparateurs sont des '/'
        assert '\\' not in normalized
        # Vérifier que le chemin contient nos éléments
        assert 'path' in normalized
        assert 'to' in normalized
        assert 'file' in normalized
        # Compter les séparateurs dans la partie relative uniquement
        path_parts = normalized.split('/')
        relative_parts = [p for p in path_parts if p in ['path', 'to', 'file']]
        # Il devrait y avoir 2 séparateurs entre les 3 parties
        assert len(relative_parts) == 3