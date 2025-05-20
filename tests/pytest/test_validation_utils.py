"""Tests pour le module utils.validation_utils."""

import pytest
from pathlib import Path

from gestvenv.utils.validation_utils import (
    is_valid_name, is_valid_path, is_safe_directory,
    matches_pattern, parse_version_string, is_valid_python_version,
    is_valid_package_name, validate_packages_list
)

class TestValidationUtils:
    """Tests pour les fonctions utilitaires de validation."""
    
    def test_is_valid_name(self) -> None:
        """Teste la validation des noms."""
        # Noms valides
        assert is_valid_name("valid_name")[0] is True
        assert is_valid_name("valid-name")[0] is True
        assert is_valid_name("valid123")[0] is True
        
        # Noms invalides
        assert is_valid_name("")[0] is False  # Vide
        assert is_valid_name("a" * 100)[0] is False  # Trop long
        assert is_valid_name("invalid@name")[0] is False  # Caractères spéciaux
        assert is_valid_name("invalid name")[0] is False  # Espaces
    
    def test_is_valid_path(self, temp_dir: Path) -> None:
        """Teste la validation des chemins."""
        # Chemin valide
        valid, path, _ = is_valid_path(temp_dir)
        assert valid is True
        assert path == temp_dir.resolve()
        
        # Chemin inexistant (mais valide comme chaîne)
        valid, path, _ = is_valid_path(temp_dir / "nonexistent")
        assert valid is True
        
        # Chemin devant exister
        valid, path, _ = is_valid_path(temp_dir / "nonexistent", must_exist=True)
        assert valid is False
        
        # Fichier vs répertoire
        test_file = temp_dir / "test_file.txt"
        test_file.touch()
        
        valid, path, _ = is_valid_path(test_file, must_be_dir=True)
        assert valid is False
        
        valid, path, _ = is_valid_path(test_file, must_be_file=True)
        assert valid is True
        
        valid, path, _ = is_valid_path(temp_dir, must_be_file=True)
        assert valid is False
    
    def test_is_safe_directory(self, temp_dir: Path) -> None:
        """Teste la vérification de sécurité des répertoires."""
        # Répertoire sécuritaire
        safe, _ = is_safe_directory(temp_dir / "safe_dir")
        assert safe is True
        
        # Répertoires système critiques
        critical_dirs = [
            "/",
            "/etc",
            "/bin",
            "C:\\Windows",
            "C:\\Program Files"
        ]
        
        for dir_path in critical_dirs:
            safe, warning = is_safe_directory(dir_path)
            assert safe is False
            assert "système critique" in warning
        
        # Exception pour les répertoires contenant "gestvenv"
        safe, _ = is_safe_directory(Path.home() / ".config" / "gestvenv")
        assert safe is True
    
    def test_matches_pattern(self) -> None:
        """Teste la vérification de correspondance aux motifs regex."""
        # Correspondances valides
        assert matches_pattern("abc123", r"^[a-z0-9]+$") is True
        assert matches_pattern("test@example.com", r"^[\w.-]+@[\w.-]+\.\w+$") is True
        
        # Correspondances invalides
        assert matches_pattern("ABC", r"^[a-z]+$") is False
        assert matches_pattern("123", r"^[a-z]+$") is False
        
        # Motif invalide
        assert matches_pattern("abc", r"[") is False
    
    def test_parse_version_string(self) -> None:
        """Teste l'analyse des chaînes de version."""
        # Versions valides
        assert parse_version_string("3.9.0") == (3, 9, 0)
        assert parse_version_string("3.9") == (3, 9)
        assert parse_version_string("3") == (3,)
        
        # Versions invalides
        assert parse_version_string("invalid") is None
        assert parse_version_string("") is None
    
    def test_is_valid_python_version(self) -> None:
        """Teste la validation des versions Python."""
        # Versions valides
        assert is_valid_python_version("python")[0] is True
        assert is_valid_python_version("python3")[0] is True
        assert is_valid_python_version("python3.9")[0] is True
        assert is_valid_python_version("3.9")[0] is True
        
        # Versions invalides
        assert is_valid_python_version("python2.7")[0] is False
        assert is_valid_python_version("2.7")[0] is False
        assert is_valid_python_version("invalid")[0] is False
    
    def test_is_valid_package_name(self) -> None:
        """Teste la validation des noms de packages."""
        # Packages valides
        assert is_valid_package_name("flask")[0] is True
        assert is_valid_package_name("flask==2.0.1")[0] is True
        assert is_valid_package_name("flask>=2.0.1")[0] is True
        assert is_valid_package_name("flask[extra]")[0] is True
        assert is_valid_package_name("git+https://github.com/user/repo.git")[0] is True
        
        # Packages invalides
        assert is_valid_package_name("")[0] is False
        assert is_valid_package_name("invalid package")[0] is False
    
    def test_validate_packages_list(self) -> None:
        """Teste la validation des listes de packages."""
        # Liste valide
        valid, packages, _ = validate_packages_list("flask,pytest,requests==2.26.0")
        assert valid is True
        assert len(packages) == 3
        assert "flask" in packages
        assert "pytest" in packages
        assert "requests==2.26.0" in packages
        
        # Liste vide
        valid, _, _ = validate_packages_list("")
        assert valid is False
        
        # Liste avec packages invalides
        valid, _, error = validate_packages_list("flask,invalid package")
        assert valid is False
        assert "invalid package" in error