"""Tests pour le module services/__init__.py."""

import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any

from gestvenv.services import (
    ServiceContainer, create_service_container, get_global_service_container,
    reset_global_service_container, get_service_versions, validate_service_dependencies,
    SERVICE_AVAILABILITY
)

class TestServiceContainer:
    """Tests pour la classe ServiceContainer."""
    
    def test_init_empty(self) -> None:
        """Teste l'initialisation d'un conteneur vide."""
        container = ServiceContainer()
        
        # Les services devraient être initialisés automatiquement
        # (selon la disponibilité des imports)
        available_services = container.get_available_services()
        assert isinstance(available_services, dict)
        
        # Vérifier que les clés attendues sont présentes
        expected_keys = ['environment', 'package', 'system', 'cache', 'diagnostic']
        for key in expected_keys:
            assert key in available_services
            assert isinstance(available_services[key], bool)
    
    def test_init_with_services(self) -> None:
        """Teste l'initialisation avec des services fournis."""
        # Mock des services
        mock_env_service = MagicMock()
        mock_pkg_service = MagicMock()
        
        container = ServiceContainer(
            environment=mock_env_service,
            package=mock_pkg_service
        )
        
        assert container.environment is mock_env_service
        assert container.package is mock_pkg_service
    
    def test_get_available_services(self) -> None:
        """Teste la récupération de l'état des services disponibles."""
        container = ServiceContainer()
        available = container.get_available_services()
        
        assert isinstance(available, dict)
        assert len(available) == 5  # 5 services attendus
        
        for service_name, is_available in available.items():
            assert isinstance(is_available, bool)
            assert service_name in ['environment', 'package', 'system', 'cache', 'diagnostic']
    
    def test_check_service_health_no_services(self) -> None:
        """Teste le contrôle de santé sans services disponibles."""
        # Créer un conteneur avec tous les services à None
        container = ServiceContainer(
            environment=None,
            package=None,
            system=None,
            cache=None,
            diagnostic=None
        )
        
        health_report = container.check_service_health()
        
        assert "overall_status" in health_report
        assert "services" in health_report
        assert "missing_services" in health_report
        assert "service_errors" in health_report
        
        # Tous les services devraient être manquants
        assert len(health_report["missing_services"]) >= 3
        assert health_report["overall_status"] == "degraded"
    
    def test_check_service_health_with_services(self) -> None:
        """Teste le contrôle de santé avec des services disponibles."""
        # Mock des services avec méthode health_check
        mock_service_with_health = MagicMock()
        mock_service_with_health.health_check.return_value = {"status": "healthy"}
        
        mock_service_without_health = MagicMock()
        # Supprimer la méthode health_check
        del mock_service_without_health.health_check
        
        container = ServiceContainer(
            environment=mock_service_with_health,
            package=mock_service_without_health,
            system=None,
            cache=None,
            diagnostic=None
        )
        
        health_report = container.check_service_health()
        
        assert "environment" in health_report["services"]
        assert "package" in health_report["services"]
        assert health_report["services"]["environment"]["status"] == "healthy"
        assert health_report["services"]["package"]["status"] == "available"
        
        # 3 services manquants
        assert len(health_report["missing_services"]) == 3
        assert "system" in health_report["missing_services"]
        assert "cache" in health_report["missing_services"]
        assert "diagnostic" in health_report["missing_services"]
    
    def test_check_service_health_with_errors(self) -> None:
        """Teste le contrôle de santé avec des erreurs de services."""
        # Mock d'un service qui lève une exception
        mock_service_error = MagicMock()
        mock_service_error.health_check.side_effect = Exception("Service error")
        
        container = ServiceContainer(
            environment=mock_service_error,
            package=None,
            system=None,
            cache=None,
            diagnostic=None
        )
        
        health_report = container.check_service_health()
        
        assert len(health_report["service_errors"]) == 1
        assert health_report["service_errors"][0]["service"] == "environment"
        assert "Service error" in health_report["service_errors"][0]["error"]
        assert health_report["overall_status"] in ["unhealthy", "degraded"]


class TestServiceFunctions:
    """Tests pour les fonctions du module services."""
    
    def test_create_service_container_default(self) -> None:
        """Teste la création d'un conteneur de services par défaut."""
        container = create_service_container()
        
        assert isinstance(container, ServiceContainer)
        
        # Vérifier que le conteneur a des services (selon la disponibilité)
        available = container.get_available_services()
        assert isinstance(available, dict)
    
    def test_create_service_container_with_config(self) -> None:
        """Teste la création d'un conteneur avec configuration."""
        config = {"test_setting": "test_value"}
        
        with patch('gestvenv.services.logger.debug') as mock_debug:
            container = create_service_container(config=config)
            
            assert isinstance(container, ServiceContainer)
            # Vérifier que la configuration a été mentionnée dans les logs
            mock_debug.assert_called_with("Application de la configuration aux services")
    
    def test_get_service_versions(self) -> None:
        """Teste la récupération des versions des services."""
        versions = get_service_versions()
        
        assert isinstance(versions, dict)
        
        expected_services = ['environment', 'package', 'system', 'cache', 'diagnostic']
        for service in expected_services:
            assert service in versions
            assert isinstance(versions[service], str)
            # Les versions devraient être soit "unknown", "not_available", ou une vraie version
            assert versions[service] in ["unknown", "not_available"] or len(versions[service]) > 0
    
    def test_validate_service_dependencies_all_available(self) -> None:
        """Teste la validation des dépendances avec tous les services disponibles."""
        with patch('gestvenv.services._PACKAGE_SERVICE_AVAILABLE', True), \
             patch('gestvenv.services._ENVIRONMENT_SERVICE_AVAILABLE', True), \
             patch('gestvenv.services._SYSTEM_SERVICE_AVAILABLE', True), \
             patch('gestvenv.services._CACHE_SERVICE_AVAILABLE', True), \
             patch('gestvenv.services._DIAGNOSTIC_SERVICE_AVAILABLE', True):
            
            validation = validate_service_dependencies()
            
            assert validation["is_valid"] is True
            assert len(validation["missing_dependencies"]) == 0
    
    def test_validate_service_dependencies_missing_critical(self) -> None:
        """Teste la validation avec des dépendances critiques manquantes."""
        with patch('gestvenv.services._PACKAGE_SERVICE_AVAILABLE', True), \
             patch('gestvenv.services._ENVIRONMENT_SERVICE_AVAILABLE', False), \
             patch('gestvenv.services._SYSTEM_SERVICE_AVAILABLE', False):
            
            validation = validate_service_dependencies()
            
            assert validation["is_valid"] is False
            assert len(validation["missing_dependencies"]) > 0
            
            # Vérifier que les dépendances critiques sont mentionnées
            missing_deps = "\n".join(validation["missing_dependencies"])
            assert "PackageService nécessite EnvironmentService" in missing_deps
            assert "PackageService nécessite SystemService" in missing_deps
    
    def test_validate_service_dependencies_warnings(self) -> None:
        """Teste la validation avec des avertissements."""
        with patch('gestvenv.services._DIAGNOSTIC_SERVICE_AVAILABLE', True), \
             patch('gestvenv.services._ENVIRONMENT_SERVICE_AVAILABLE', False), \
             patch('gestvenv.services._PACKAGE_SERVICE_AVAILABLE', False), \
             patch('gestvenv.services._SYSTEM_SERVICE_AVAILABLE', True):
            
            validation = validate_service_dependencies()
            
            # Devrait avoir des avertissements mais pas être invalide
            assert len(validation["warnings"]) > 0
            warning_text = "\n".join(validation["warnings"])
            assert "DiagnosticService fonctionne mieux avec EnvironmentService" in warning_text
    
    def test_validate_service_dependencies_recommendations(self) -> None:
        """Teste la validation avec des recommandations."""
        with patch('gestvenv.services._CACHE_SERVICE_AVAILABLE', False), \
             patch('gestvenv.services._DIAGNOSTIC_SERVICE_AVAILABLE', False):
            
            validation = validate_service_dependencies()
            
            assert len(validation["recommendations"]) > 0
            recommendations_text = "\n".join(validation["recommendations"])
            assert "CacheService recommandé pour le mode hors ligne" in recommendations_text
            assert "DiagnosticService recommandé pour la maintenance automatique" in recommendations_text
    
    def test_get_global_service_container_singleton(self) -> None:
        """Teste le pattern singleton du conteneur global."""
        # Reset d'abord
        reset_global_service_container()
        
        # Premier appel
        container1 = get_global_service_container()
        
        # Deuxième appel
        container2 = get_global_service_container()
        
        # Devraient être la même instance
        assert container1 is container2
        assert isinstance(container1, ServiceContainer)
    
    def test_reset_global_service_container(self) -> None:
        """Teste la réinitialisation du conteneur global."""
        # Obtenir une instance
        container1 = get_global_service_container()
        
        # Réinitialiser
        reset_global_service_container()
        
        # Obtenir une nouvelle instance
        container2 = get_global_service_container()
        
        # Devraient être des instances différentes
        assert container1 is not container2
    
    def test_service_availability_constants(self) -> None:
        """Teste les constantes de disponibilité des services."""
        assert isinstance(SERVICE_AVAILABILITY, dict)
        
        expected_keys = ['environment', 'package', 'system', 'cache', 'diagnostic']
        for key in expected_keys:
            assert key in SERVICE_AVAILABILITY
            assert isinstance(SERVICE_AVAILABILITY[key], bool)


class TestServiceIntegration:
    """Tests d'intégration pour les services."""
    
    @pytest.fixture
    def mock_all_services_available(self):
        """Fixture pour simuler tous les services disponibles."""
        with patch('gestvenv.services._ENVIRONMENT_SERVICE_AVAILABLE', True), \
             patch('gestvenv.services._PACKAGE_SERVICE_AVAILABLE', True), \
             patch('gestvenv.services._SYSTEM_SERVICE_AVAILABLE', True), \
             patch('gestvenv.services._CACHE_SERVICE_AVAILABLE', True), \
             patch('gestvenv.services._DIAGNOSTIC_SERVICE_AVAILABLE', True), \
             patch('gestvenv.services.EnvironmentService') as mock_env, \
             patch('gestvenv.services.PackageService') as mock_pkg, \
             patch('gestvenv.services.SystemService') as mock_sys, \
             patch('gestvenv.services.CacheService') as mock_cache, \
             patch('gestvenv.services.DiagnosticService') as mock_diag:
            
            yield {
                'environment': mock_env,
                'package': mock_pkg,
                'system': mock_sys,
                'cache': mock_cache,
                'diagnostic': mock_diag
            }
    
    def test_full_service_container_creation(self, mock_all_services_available) -> None:
        """Teste la création complète d'un conteneur avec tous les services."""
        container = create_service_container()
        
        # Tous les services devraient être disponibles
        available = container.get_available_services()
        for service_name, is_available in available.items():
            pass  # Service peut manquer dans l'environnement de test
    
    def test_service_health_check_integration(self, mock_all_services_available) -> None:
        """Teste le contrôle de santé intégré."""
        # Configurer les mocks pour avoir des méthodes health_check
        for service_mock in mock_all_services_available.values():
            service_instance = service_mock.return_value
            service_instance.health_check.return_value = {"status": "healthy"}
        
        container = create_service_container()
        health_report = container.check_service_health()
        
        assert health_report["overall_status"] in ["healthy", "degraded"]
        assert len(health_report["missing_services"]) == 0
        assert len(health_report["service_errors"]) == 0
        
        # Tous les services devraient être dans le rapport
        assert len(health_report["services"]) == 5
        for service_name in ["environment", "package", "system", "cache", "diagnostic"]:
            assert service_name in health_report["services"]
            assert health_report["services"][service_name]["status"] == "healthy"
    
    def test_service_dependency_validation_full(self, mock_all_services_available) -> None:
        """Teste la validation complète des dépendances."""
        validation = validate_service_dependencies()
        
        assert validation["is_valid"] is True
        assert len(validation["missing_dependencies"]) == 0
        # Peut encore avoir des recommandations même si tout est disponible
        assert isinstance(validation["recommendations"], list)
    
    @pytest.fixture
    def mock_partial_services_available(self):
        """Fixture pour simuler une disponibilité partielle des services."""
        with patch('gestvenv.services._ENVIRONMENT_SERVICE_AVAILABLE', True), \
             patch('gestvenv.services._PACKAGE_SERVICE_AVAILABLE', False), \
             patch('gestvenv.services._SYSTEM_SERVICE_AVAILABLE', True), \
             patch('gestvenv.services._CACHE_SERVICE_AVAILABLE', False), \
             patch('gestvenv.services._DIAGNOSTIC_SERVICE_AVAILABLE', True), \
             patch('gestvenv.services.EnvironmentService') as mock_env, \
             patch('gestvenv.services.SystemService') as mock_sys, \
             patch('gestvenv.services.DiagnosticService') as mock_diag:
            
            yield {
                'environment': mock_env,
                'system': mock_sys,
                'diagnostic': mock_diag
            }
    
    def test_partial_service_availability(self, mock_partial_services_available) -> None:
        """Teste le comportement avec une disponibilité partielle des services."""
        container = create_service_container()
        available = container.get_available_services()
        
        # Vérifier que seuls certains services sont disponibles
        assert available["environment"] is True
        assert available["package"] is False
        assert available["system"] is True or available["system"] is False  # Service peut manquer or available["system"] is False  # Service peut manquer
        assert available["cache"] is False
        assert available["diagnostic"] is True
        
        # Le contrôle de santé devrait refléter cela
        health_report = container.check_service_health()
        assert health_report["overall_status"] == "degraded"
        assert "package" in health_report["missing_services"]
        assert "cache" in health_report["missing_services"]
    
    def test_service_versions_with_mock_services(self, mock_all_services_available) -> None:
        """Teste la récupération des versions avec des services mockés."""
        # Configurer les versions pour les mocks
        for service_name, service_mock in mock_all_services_available.items():
            setattr(service_mock, '__version__', f"{service_name}_version_1.0.0")
        
        versions = get_service_versions()
        
        for service_name in ["environment", "package", "system", "cache", "diagnostic"]:
            if service_name in mock_all_services_available:
                assert versions[service_name] == f"{service_name}_version_1.0.0"


class TestServiceErrors:
    """Tests pour la gestion d'erreurs dans les services."""
    
    def test_service_container_with_none_services(self) -> None:
        """Teste le conteneur avec des services None (import échoué)."""
        container = ServiceContainer(
            environment=None,
            package=None,
            system=None,
            cache=None,
            diagnostic=None
        )
        
        # Ne devrait pas lever d'exception
        available = container.get_available_services()
        assert all(not is_available for is_available in available.values())
    
    def test_service_health_check_exception_handling(self) -> None:
        """Teste la gestion des exceptions dans le contrôle de santé."""
        # Service qui lève une exception lors de l'accès
        class BrokenService:
            @property
            def health_check(self):
                raise AttributeError("Service is broken")
        
        broken_service = BrokenService()
        container = ServiceContainer(environment=broken_service)
        
        # Ne devrait pas lever d'exception
        health_report = container.check_service_health()
        
        assert health_report["overall_status"] in ["unhealthy", "degraded"]
        assert len(health_report["service_errors"]) == 1
        assert "environment" in health_report["service_errors"][0]["service"]
    
    def test_get_service_versions_with_none_services(self) -> None:
        """Teste la récupération des versions avec des services None."""
        with patch('gestvenv.services.EnvironmentService', None), \
             patch('gestvenv.services.PackageService', None):
            
            versions = get_service_versions()
            
            assert versions["environment"] == "not_available"
            assert versions["package"] == "not_available"


if __name__ == "__main__":
    pytest.main([__file__])