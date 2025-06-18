"""
Tests unitaires pour les exceptions
"""

import pytest
from unittest.mock import Mock

from gestvenv.core.exceptions import (
    GestVenvError,
    EnvironmentError,
    BackendError,
    ConfigurationError,
    ValidationError,
    SecurityValidationError,
    MigrationError,
    CacheError,
    TemplateError,
    DiagnosticError,
    BackendNotAvailableError,
    EnvironmentNotFoundError,
    EnvironmentExistsError,
    PackageInstallationError,
    PyProjectParsingError,
    RequirementsParsingError
)


class TestGestVenvError:
    """Tests pour GestVenvError (classe de base)"""
    
    def test_creation_message_simple(self):
        """Test création avec message simple"""
        error = GestVenvError("Message d'erreur")
        
        assert str(error) == "Message d'erreur"
        assert error.details is None

    def test_creation_avec_details(self):
        """Test création avec détails"""
        details = {"key": "value", "number": 42}
        error = GestVenvError("Message", details=details)
        
        assert str(error) == "Message"
        assert error.details == details

    def test_heritage_exception(self):
        """Test héritage Exception"""
        error = GestVenvError("Test")
        
        assert isinstance(error, Exception)
        assert isinstance(error, GestVenvError)

    def test_details_optionnels(self):
        """Test détails optionnels"""
        error = GestVenvError("Test")
        
        assert error.details is None

    def test_details_modification(self):
        """Test modification détails"""
        error = GestVenvError("Test")
        error.details = {"added": "later"}
        
        assert error.details["added"] == "later"


class TestEnvironmentError:
    """Tests pour EnvironmentError"""
    
    def test_creation_basique(self):
        """Test création basique"""
        error = EnvironmentError("Erreur environnement")
        
        assert str(error) == "Erreur environnement"
        assert error.environment_name is None

    def test_creation_avec_nom_environnement(self):
        """Test création avec nom environnement"""
        error = EnvironmentError("Erreur", environment_name="test_env")
        
        assert str(error) == "Erreur"
        assert error.environment_name == "test_env"

    def test_creation_complete(self):
        """Test création complète"""
        details = {"path": "/test/env"}
        error = EnvironmentError(
            "Erreur environnement",
            environment_name="test_env",
            details=details
        )
        
        assert str(error) == "Erreur environnement"
        assert error.environment_name == "test_env"
        assert error.details == details

    def test_heritage_gestvenv_error(self):
        """Test héritage GestVenvError"""
        error = EnvironmentError("Test")
        
        assert isinstance(error, GestVenvError)
        assert isinstance(error, EnvironmentError)


class TestBackendError:
    """Tests pour BackendError"""
    
    def test_creation_basique(self):
        """Test création basique"""
        error = BackendError("Erreur backend")
        
        assert str(error) == "Erreur backend"
        assert error.backend_name is None

    def test_creation_avec_backend(self):
        """Test création avec nom backend"""
        error = BackendError("Erreur", backend_name="uv")
        
        assert str(error) == "Erreur"
        assert error.backend_name == "uv"

    def test_creation_complete(self):
        """Test création complète"""
        details = {"version": "0.1.0"}
        error = BackendError(
            "Backend indisponible",
            backend_name="uv",
            details=details
        )
        
        assert str(error) == "Backend indisponible"
        assert error.backend_name == "uv"
        assert error.details == details


class TestConfigurationError:
    """Tests pour ConfigurationError"""
    
    def test_creation_basique(self):
        """Test création basique"""
        error = ConfigurationError("Erreur configuration")
        
        assert str(error) == "Erreur configuration"
        assert error.config_path is None

    def test_creation_avec_chemin(self):
        """Test création avec chemin config"""
        error = ConfigurationError("Erreur", config_path="/path/config.json")
        
        assert str(error) == "Erreur"
        assert error.config_path == "/path/config.json"

    def test_heritage_gestvenv_error(self):
        """Test héritage"""
        error = ConfigurationError("Test")
        
        assert isinstance(error, GestVenvError)


class TestValidationError:
    """Tests pour ValidationError"""
    
    def test_creation_basique(self):
        """Test création basique"""
        error = ValidationError("Validation échouée")
        
        assert str(error) == "Validation échouée"
        assert error.field_name is None
        assert error.invalid_value is None

    def test_creation_avec_champ(self):
        """Test création avec champ"""
        error = ValidationError(
            "Valeur invalide",
            field_name="python_version",
            invalid_value="invalid"
        )
        
        assert str(error) == "Valeur invalide"
        assert error.field_name == "python_version"
        assert error.invalid_value == "invalid"

    def test_heritage_gestvenv_error(self):
        """Test héritage"""
        error = ValidationError("Test")
        
        assert isinstance(error, GestVenvError)


class TestSecurityValidationError:
    """Tests pour SecurityValidationError"""
    
    def test_creation_basique(self):
        """Test création basique"""
        error = SecurityValidationError("Sécurité compromise")
        
        assert str(error) == "Sécurité compromise"
        assert error.security_context is None

    def test_creation_avec_contexte(self):
        """Test création avec contexte sécurité"""
        error = SecurityValidationError(
            "Path traversal détecté",
            security_context="path_validation"
        )
        
        assert str(error) == "Path traversal détecté"
        assert error.security_context == "path_validation"

    def test_heritage_validation_error(self):
        """Test héritage ValidationError"""
        error = SecurityValidationError("Test")
        
        assert isinstance(error, ValidationError)
        assert isinstance(error, SecurityValidationError)


class TestMigrationError:
    """Tests pour MigrationError"""
    
    def test_creation_basique(self):
        """Test création basique"""
        error = MigrationError("Erreur migration")
        
        assert str(error) == "Erreur migration"
        assert error.from_version is None
        assert error.to_version is None

    def test_creation_avec_versions(self):
        """Test création avec versions"""
        error = MigrationError(
            "Migration échouée",
            from_version="1.0.0",
            to_version="1.1.0"
        )
        
        assert str(error) == "Migration échouée"
        assert error.from_version == "1.0.0"
        assert error.to_version == "1.1.0"

    def test_creation_complete(self):
        """Test création complète"""
        details = {"backup_path": "/backup"}
        error = MigrationError(
            "Migration échouée",
            from_version="1.0.0",
            to_version="1.1.0",
            details=details
        )
        
        assert error.details == details


class TestCacheError:
    """Tests pour CacheError"""
    
    def test_creation_basique(self):
        """Test création basique"""
        error = CacheError("Erreur cache")
        
        assert str(error) == "Erreur cache"
        assert error.cache_operation is None

    def test_creation_avec_operation(self):
        """Test création avec opération"""
        error = CacheError("Cache corrompue", cache_operation="read")
        
        assert str(error) == "Cache corrompue"
        assert error.cache_operation == "read"


class TestTemplateError:
    """Tests pour TemplateError"""
    
    def test_creation_basique(self):
        """Test création basique"""
        error = TemplateError("Erreur template")
        
        assert str(error) == "Erreur template"
        assert error.template_name is None

    def test_creation_avec_template(self):
        """Test création avec nom template"""
        error = TemplateError("Template invalide", template_name="web_app")
        
        assert str(error) == "Template invalide"
        assert error.template_name == "web_app"


class TestDiagnosticError:
    """Tests pour DiagnosticError"""
    
    def test_creation_basique(self):
        """Test création basique"""
        error = DiagnosticError("Erreur diagnostic")
        
        assert str(error) == "Erreur diagnostic"
        assert error.diagnostic_type is None
        assert error.environment_name is None

    def test_creation_complete(self):
        """Test création complète"""
        details = {"failed_checks": ["python", "packages"]}
        error = DiagnosticError(
            "Diagnostic échoué",
            diagnostic_type="health_check",
            environment_name="test_env",
            details=details
        )
        
        assert str(error) == "Diagnostic échoué"
        assert error.diagnostic_type == "health_check"
        assert error.environment_name == "test_env"
        assert error.details == details


class TestExceptionsSpecialisees:
    """Tests pour les exceptions spécialisées"""
    
    def test_backend_not_available_error(self):
        """Test BackendNotAvailableError"""
        error = BackendNotAvailableError("uv non disponible", backend_name="uv")
        
        assert isinstance(error, BackendError)
        assert str(error) == "uv non disponible"
        assert error.backend_name == "uv"

    def test_environment_not_found_error(self):
        """Test EnvironmentNotFoundError"""
        error = EnvironmentNotFoundError("Environnement introuvable", environment_name="missing")
        
        assert isinstance(error, EnvironmentError)
        assert str(error) == "Environnement introuvable"
        assert error.environment_name == "missing"

    def test_environment_exists_error(self):
        """Test EnvironmentExistsError"""
        error = EnvironmentExistsError("Environnement existe", environment_name="existing")
        
        assert isinstance(error, EnvironmentError)
        assert str(error) == "Environnement existe"
        assert error.environment_name == "existing"

    def test_package_installation_error(self):
        """Test PackageInstallationError"""
        details = {"exit_code": 1}
        error = PackageInstallationError(
            "Installation échouée",
            package_name="requests",
            backend_name="pip",
            details=details
        )
        
        assert isinstance(error, BackendError)
        assert str(error) == "Installation échouée"
        assert error.package_name == "requests"
        assert error.backend_name == "pip"
        assert error.details == details

    def test_pyproject_parsing_error(self):
        """Test PyProjectParsingError"""
        error = PyProjectParsingError(
            "Erreur parsing",
            file_path="/project/pyproject.toml",
            line_number=15
        )
        
        assert isinstance(error, ValidationError)
        assert str(error) == "Erreur parsing"
        assert error.file_path == "/project/pyproject.toml"
        assert error.line_number == 15

    def test_requirements_parsing_error(self):
        """Test RequirementsParsingError"""
        error = RequirementsParsingError(
            "Ligne invalide",
            file_path="/project/requirements.txt",
            line_number=5,
            line_content="invalid-line"
        )
        
        assert isinstance(error, ValidationError)
        assert str(error) == "Ligne invalide"
        assert error.file_path == "/project/requirements.txt"
        assert error.line_number == 5
        assert error.line_content == "invalid-line"


class TestUtilisationExceptions:
    """Tests d'utilisation pratique des exceptions"""
    
    def test_capture_gestvenv_error(self):
        """Test capture erreur GestVenv générique"""
        def raise_specific_error():
            raise EnvironmentError("Erreur spécifique")
        
        with pytest.raises(GestVenvError):
            raise_specific_error()

    def test_capture_erreur_specifique(self):
        """Test capture erreur spécifique"""
        def raise_env_error():
            raise EnvironmentNotFoundError("Env not found", environment_name="missing")
        
        try:
            raise_env_error()
        except EnvironmentNotFoundError as e:
            assert e.environment_name == "missing"
        except EnvironmentError:
            pytest.fail("Devrait capturer EnvironmentNotFoundError")

    def test_informations_contextuelles(self):
        """Test récupération informations contextuelles"""
        details = {
            "path": "/test/env",
            "python_version": "3.11",
            "backend": "uv"
        }
        
        error = EnvironmentError(
            "Création échouée",
            environment_name="test_env",
            details=details
        )
        
        # Récupération des informations pour logging/debugging
        assert error.environment_name == "test_env"
        assert error.details["path"] == "/test/env"
        assert error.details["python_version"] == "3.11"
        assert error.details["backend"] == "uv"

    def test_chaining_exceptions(self):
        """Test chaînage exceptions"""
        try:
            raise ValueError("Erreur originale")
        except ValueError as original:
            # Transformation en exception GestVenv
            new_error = ConfigurationError("Erreur configuration")
            new_error.__cause__ = original
            
            assert new_error.__cause__ is original
            assert str(new_error.__cause__) == "Erreur originale"

    def test_exception_avec_suggestion(self):
        """Test exception avec suggestion correction"""
        details = {
            "suggestion": "Utiliser 'gestvenv doctor' pour diagnostiquer",
            "command": "gestvenv doctor test_env"
        }
        
        error = EnvironmentError(
            "Environnement corrompu",
            environment_name="test_env",
            details=details
        )
        
        assert "suggestion" in error.details
        assert "command" in error.details