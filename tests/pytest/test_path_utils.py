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
        # Simuler un chemin utilisateur
        monkeypatch.setattr(Path, 'home', lambda: Path('/home/testuser'))
        
        # Tester l'expansion
        path = expand_user_path("~/test/path")
        assert str(path) == "/home/testuser/test/path"
        
        # Tester un chemin sans ~ (ne devrait pas changer)
        path = expand_user_path("/tmp/test")
        assert str(path) == "/tmp/test"
    
    def test_resolve_path(self, monkeypatch: MonkeyPatch) -> None:
        """Teste la résolution des chemins relatifs et absolus."""
        # Simuler le répertoire courant
        monkeypatch.setattr(Path, 'cwd', lambda: Path('/current/dir'))
        monkeypatch.setattr(Path, 'home', lambda: Path('/home/testuser'))
        
        # Tester un chemin absolu
        path = resolve_path("/absolute/path")
        assert path.is_absolute()
        assert str(path) == "/absolute/path"
        
        # Tester un chemin relatif
        path = resolve_path("relative/path")
        assert path.is_absolute()
        assert str(path) == "/current/dir/relative/path"
        
        # Tester un chemin utilisateur
        path = resolve_path("~/user/path")
        assert path.is_absolute()
        assert str(path) == "/home/testuser/user/path"
    
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
        assert result == test_dir
    
    def test_get_default_data_dir(self, monkeypatch: MonkeyPatch) -> None:
        """Teste la récupération du répertoire de données par défaut."""
        # Simuler différents systèmes d'exploitation
        with patch('gestvenv.utils.path_utils.get_os_name') as mock_os:
            # Windows
            mock_os.return_value = 'windows'
            monkeypatch.setenv('APPDATA', '/windows/appdata')
            
            data_dir = get_default_data_dir()
            assert 'GestVenv' in str(data_dir)
            assert '/windows/appdata' in str(data_dir)
            
            # macOS
            mock_os.return_value = 'darwin'
            monkeypatch.setattr(Path, 'home', lambda: Path('/Users/testuser'))
            
            data_dir = get_default_data_dir()
            assert 'GestVenv' in str(data_dir)
            assert 'Library/Application Support' in str(data_dir)
            
            # Linux
            mock_os.return_value = 'linux'
            monkeypatch.setattr(Path, 'home', lambda: Path('/home/testuser'))
            
            data_dir = get_default_data_dir()
            assert 'gestvenv' in str(data_dir)
            assert '.config' in str(data_dir)
    
    def test_get_normalized_path(self) -> None:
        """Teste la normalisation des chemins."""
        # Créer un chemin avec des séparateurs spécifiques à la plateforme
        path = os.path.join('path', 'to', 'file')
        
        # Normaliser le chemin
        normalized = get_normalized_path(path)
        
        # Vérifier que tous les séparateurs sont des '/'
        assert '\\' not in normalized
        assert normalized.count('/') == 2  # deux séparateurs pour 'path/to/file'