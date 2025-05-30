"""
Services pour GestVenv.

Ce package contient l'ensemble des services responsables des opérations métier de GestVenv.
Il fournit une interface unifiée pour accéder à tous les services de l'application et gère
les dépendances entre les différents modules.

Services disponibles:
- EnvironmentService: Opérations sur les environnements virtuels (création, suppression, validation)
- PackageService: Gestion des packages Python (installation, mise à jour, désinstallation)
- SystemService: Interactions avec le système d'exploitation (commandes, processus, informations système)
- CacheService: Gestion du cache de packages pour le mode hors ligne
- DiagnosticService: Diagnostic et réparation automatique des environnements

Architecture:
Les services sont conçus selon le principe de responsabilité unique et peuvent être utilisés
indépendamment ou en composition. Certains services dépendent d'autres services :
- PackageService utilise EnvironmentService, SystemService et CacheService
- DiagnosticService utilise tous les autres services
- EnvironmentService et SystemService sont largement indépendants

Usage:
    from gestvenv.services import EnvironmentService, PackageService
    
    env_service = EnvironmentService()
    pkg_service = PackageService()
    
    # Ou utiliser la factory pour des instances préconfigurées
    from gestvenv.services import create_service_container
    
    services = create_service_container()
    env_service = services.environment
    pkg_service = services.package
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

# Configuration du logger pour le module services
logger = logging.getLogger(__name__)

# Imports des services principaux
try:
    from .environment_service import EnvironmentService
    _ENVIRONMENT_SERVICE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"EnvironmentService non disponible: {e}")
    EnvironmentService = None
    _ENVIRONMENT_SERVICE_AVAILABLE = False

try:
    from .package_service import PackageService
    _PACKAGE_SERVICE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"PackageService non disponible: {e}")
    PackageService = None
    _PACKAGE_SERVICE_AVAILABLE = False

try:
    from .system_service import SystemService
    _SYSTEM_SERVICE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"SystemService non disponible: {e}")
    SystemService = None
    _SYSTEM_SERVICE_AVAILABLE = False

try:
    from .cache_service import CacheService
    _CACHE_SERVICE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"CacheService non disponible: {e}")
    CacheService = None
    _CACHE_SERVICE_AVAILABLE = False

try:
    from .diagnostic_services import DiagnosticService
    _DIAGNOSTIC_SERVICE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"DiagnosticService non disponible: {e}")
    DiagnosticService = None
    _DIAGNOSTIC_SERVICE_AVAILABLE = False


@dataclass
class ServiceContainer:
    """
    Conteneur pour tous les services GestVenv.
    
    Fournit un accès centralisé à tous les services avec gestion des dépendances
    et initialisation paresseuse.
    """
    environment: Optional[EnvironmentService] = None
    package: Optional[PackageService] = None
    system: Optional[SystemService] = None
    cache: Optional[CacheService] = None
    diagnostic: Optional[DiagnosticService] = None
    
    def __post_init__(self):
        """Initialise les services avec gestion des dépendances."""
        # Créer les instances des services si les classes sont disponibles
        if self.system is None and _SYSTEM_SERVICE_AVAILABLE:
            self.system = SystemService()
        
        if self.environment is None and _ENVIRONMENT_SERVICE_AVAILABLE:
            self.environment = EnvironmentService()
        
        if self.cache is None and _CACHE_SERVICE_AVAILABLE:
            self.cache = CacheService()
        
        if self.package is None and _PACKAGE_SERVICE_AVAILABLE:
            self.package = PackageService()
        
        if self.diagnostic is None and _DIAGNOSTIC_SERVICE_AVAILABLE:
            self.diagnostic = DiagnosticService()
    
    def get_available_services(self) -> Dict[str, bool]:
        """
        Retourne l'état de disponibilité de tous les services.
        
        Returns:
            Dict: Dictionnaire avec l'état de chaque service
        """
        return {
            'environment': self.environment is not None,
            'package': self.package is not None,
            'system': self.system is not None,
            'cache': self.cache is not None,
            'diagnostic': self.diagnostic is not None
        }
    
    def check_service_health(self) -> Dict[str, Any]:
        """
        Vérifie l'état de santé de tous les services disponibles.
        
        Returns:
            Dict: Rapport de santé de chaque service
        """
        health_report = {
            'overall_status': 'healthy',
            'services': {},
            'missing_services': [],
            'service_errors': []
        }
        
        # Vérifier chaque service
        for service_name, is_available in self.get_available_services().items():
            if not is_available:
                health_report['missing_services'].append(service_name)
                health_report['overall_status'] = 'degraded'
            else:
                try:
                    service = getattr(self, service_name)
                    # Test basique de fonctionnement du service
                    if hasattr(service, 'health_check'):
                        service_health = service.health_check()
                        health_report['services'][service_name] = service_health
                    else:
                        health_report['services'][service_name] = {'status': 'available'}
                except Exception as e:
                    health_report['service_errors'].append({
                        'service': service_name,
                        'error': str(e)
                    })
                    health_report['overall_status'] = 'unhealthy'
        
        return health_report


def create_service_container(config: Optional[Dict[str, Any]] = None) -> ServiceContainer:
    """
    Factory pour créer un conteneur de services préconfigué.
    
    Args:
        config: Configuration optionnelle pour les services
        
    Returns:
        ServiceContainer: Conteneur avec tous les services disponibles
    """
    container = ServiceContainer()
    
    # Appliquer la configuration si fournie
    if config:
        logger.debug("Application de la configuration aux services")
        # La configuration pourrait être utilisée pour personnaliser les services
        # Par exemple, pour définir des chemins personnalisés, des modes de fonctionnement, etc.
    
    return container


def get_service_versions() -> Dict[str, str]:
    """
    Retourne les versions des services disponibles.
    
    Returns:
        Dict: Versions de chaque service
    """
    versions = {}
    
    # Essayer d'obtenir les versions depuis les modules
    for service_name, service_class in [
        ('environment', EnvironmentService),
        ('package', PackageService),
        ('system', SystemService),
        ('cache', CacheService),
        ('diagnostic', DiagnosticService)
    ]:
        if service_class is not None:
            version = getattr(service_class, '__version__', 'unknown')
            versions[service_name] = version
        else:
            versions[service_name] = 'not_available'
    
    return versions


def validate_service_dependencies() -> Dict[str, Any]:
    """
    Valide que toutes les dépendances entre services sont satisfaites.
    
    Returns:
        Dict: Rapport de validation des dépendances
    """
    validation_report = {
        'is_valid': True,
        'missing_dependencies': [],
        'warnings': [],
        'recommendations': []
    }
    
    # Vérifier les dépendances critiques
    if _PACKAGE_SERVICE_AVAILABLE and not _ENVIRONMENT_SERVICE_AVAILABLE:
        validation_report['is_valid'] = False
        validation_report['missing_dependencies'].append(
            "PackageService nécessite EnvironmentService"
        )
    
    if _PACKAGE_SERVICE_AVAILABLE and not _SYSTEM_SERVICE_AVAILABLE:
        validation_report['is_valid'] = False
        validation_report['missing_dependencies'].append(
            "PackageService nécessite SystemService"
        )
    
    if _DIAGNOSTIC_SERVICE_AVAILABLE and not _ENVIRONMENT_SERVICE_AVAILABLE:
        validation_report['warnings'].append(
            "DiagnosticService fonctionne mieux avec EnvironmentService"
        )
    
    # Ajouter des recommandations
    if not _CACHE_SERVICE_AVAILABLE:
        validation_report['recommendations'].append(
            "CacheService recommandé pour le mode hors ligne"
        )
    
    if not _DIAGNOSTIC_SERVICE_AVAILABLE:
        validation_report['recommendations'].append(
            "DiagnosticService recommandé pour la maintenance automatique"
        )
    
    return validation_report


# Instance globale du conteneur de services (lazy loading)
_global_service_container: Optional[ServiceContainer] = None


def get_global_service_container() -> ServiceContainer:
    """
    Retourne l'instance globale du conteneur de services.
    
    Utilise le pattern singleton pour éviter de créer plusieurs instances
    des services en mémoire.
    
    Returns:
        ServiceContainer: Instance globale du conteneur
    """
    global _global_service_container
    
    if _global_service_container is None:
        _global_service_container = create_service_container()
        logger.debug("Conteneur de services global créé")
    
    return _global_service_container


def reset_global_service_container() -> None:
    """
    Réinitialise l'instance globale du conteneur de services.
    
    Utile pour les tests ou lors de changements de configuration.
    """
    global _global_service_container
    _global_service_container = None
    logger.debug("Conteneur de services global réinitialisé")


# Export des classes et fonctions principales
__all__ = [
    # Classes de services
    'EnvironmentService',
    'PackageService', 
    'SystemService',
    'CacheService',
    'DiagnosticService',
    
    # Conteneur et factory
    'ServiceContainer',
    'create_service_container',
    'get_global_service_container',
    'reset_global_service_container',
    
    # Fonctions utilitaires
    'get_service_versions',
    'validate_service_dependencies',
]

# Variables de disponibilité pour usage externe
SERVICE_AVAILABILITY = {
    'environment': _ENVIRONMENT_SERVICE_AVAILABLE,
    'package': _PACKAGE_SERVICE_AVAILABLE,
    'system': _SYSTEM_SERVICE_AVAILABLE,
    'cache': _CACHE_SERVICE_AVAILABLE,
    'diagnostic': _DIAGNOSTIC_SERVICE_AVAILABLE,
}

# Log de l'état d'initialisation du module
logger.debug(f"Module services initialisé. Services disponibles: {SERVICE_AVAILABILITY}")

# Validation automatique au chargement du module
_validation_result = validate_service_dependencies()
if not _validation_result['is_valid']:
    logger.error(f"Dépendances de services non satisfaites: {_validation_result['missing_dependencies']}")
elif _validation_result['warnings']:
    logger.warning(f"Avertissements de dépendances: {_validation_result['warnings']}")