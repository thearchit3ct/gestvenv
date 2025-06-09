"""
Services pour GestVenv v1.1.

Ce package contient l'ensemble des services responsables des opérations métier de GestVenv.
Il fournit une interface unifiée pour accéder à tous les services de l'application et gère
les dépendances entre les différents modules.

Services disponibles:
- EnvironmentService: Opérations sur les environnements virtuels (création, suppression, validation)
- PackageService: Gestion des packages Python (installation, mise à jour, désinstallation)
- SystemService: Interactions avec le système d'exploitation (commandes, processus, informations système)
- CacheService: Gestion du cache de packages pour le mode hors ligne
- DiagnosticService: Diagnostic et réparation automatique des environnements
- MigrationService: Migration entre versions et formats (nouveau v1.1)

Architecture:
Les services sont conçus selon le principe de responsabilité unique et peuvent être utilisés
indépendamment ou en composition via ServiceContainer.

Dépendances inter-services:
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

# Imports des services principaux avec gestion d'erreurs robuste
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

# CORRECTION: Import correct du DiagnosticService
try:
    from .diagnostic_service import DiagnosticService  # Corrigé: sans 's' à la fin
    _DIAGNOSTIC_SERVICE_AVAILABLE = True
except ImportError as e:
    # Fallback vers l'ancien nom avec 's'
    try:
        from .diagnostic_services import DiagnosticService
        _DIAGNOSTIC_SERVICE_AVAILABLE = True
        logger.info("Utilisation du nom de fichier legacy diagnostic_services.py")
    except ImportError as e2:
        logger.warning(f"DiagnosticService non disponible: {e}, {e2}")
        DiagnosticService = None
        _DIAGNOSTIC_SERVICE_AVAILABLE = False

try:
    from .migration_service import MigrationService
    _MIGRATION_SERVICE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"MigrationService non disponible: {e}")
    MigrationService = None
    _MIGRATION_SERVICE_AVAILABLE = False

@dataclass
class ServiceContainer:
    """
    Conteneur pour tous les services GestVenv.
    
    Fournit un accès centralisé à tous les services avec gestion des dépendances
    et initialisation paresseuse.
    
    Attributes:
        environment: Service de gestion des environnements virtuels
        package: Service de gestion des packages Python
        system: Service d'interaction avec le système
        cache: Service de cache pour mode hors ligne
        diagnostic: Service de diagnostic et réparation
        migration: Service de migration entre versions
    """
    environment: Optional[EnvironmentService] = None
    package: Optional[PackageService] = None
    system: Optional[SystemService] = None
    cache: Optional[CacheService] = None
    diagnostic: Optional[DiagnosticService] = None
    migration: Optional[MigrationService] = None
    
    def __post_init__(self) -> None:
        """Initialise les services avec gestion des dépendances."""
        # Services de base (indépendants)
        if not self.system and _SYSTEM_SERVICE_AVAILABLE:
            self.system = SystemService()
            
        if not self.cache and _CACHE_SERVICE_AVAILABLE:
            self.cache = CacheService()
            
        # Services dépendants
        if not self.environment and _ENVIRONMENT_SERVICE_AVAILABLE:
            self.environment = EnvironmentService(system_service=self.system)
            
        if not self.package and _PACKAGE_SERVICE_AVAILABLE:
            self.package = PackageService(
                environment_service=self.environment,
                system_service=self.system,
                cache_service=self.cache
            )
            
        if not self.migration and _MIGRATION_SERVICE_AVAILABLE:
            self.migration = MigrationService(
                system_service=self.system
            )
            
        # Service de diagnostic (utilise tous les autres)
        if not self.diagnostic and _DIAGNOSTIC_SERVICE_AVAILABLE:
            self.diagnostic = DiagnosticService(
                environment_service=self.environment,
                package_service=self.package,
                system_service=self.system,
                cache_service=self.cache,
                migration_service=self.migration
            )
    
    def is_fully_loaded(self) -> bool:
        """Vérifie si tous les services sont chargés."""
        return all([
            self.environment is not None,
            self.package is not None,
            self.system is not None,
            self.cache is not None,
            self.diagnostic is not None,
            self.migration is not None,
        ])
    
    def get_available_services(self) -> list:
        """Retourne la liste des services disponibles."""
        services = []
        if self.environment: services.append('environment')
        if self.package: services.append('package')
        if self.system: services.append('system')
        if self.cache: services.append('cache')
        if self.diagnostic: services.append('diagnostic')
        if self.migration: services.append('migration')
        return services


def create_service_container(config: Optional[Dict[str, Any]] = None) -> ServiceContainer:
    """
    Factory pour créer un conteneur de services préconfigurés.
    
    Args:
        config: Configuration optionnelle pour les services
        
    Returns:
        ServiceContainer: Conteneur avec tous les services initialisés
        
    Example:
        >>> services = create_service_container()
        >>> result = services.environment.create_environment("test", "python3.11", Path("/tmp/test"))
    """
    config = config or {}
    
    # Initialiser les services de base en premier
    system_service = SystemService(config.get('system', {})) if _SYSTEM_SERVICE_AVAILABLE else None
    environment_service = EnvironmentService(
        system_service=system_service,
        config=config.get('environment', {})
    ) if _ENVIRONMENT_SERVICE_AVAILABLE else None
    
    cache_service = CacheService(config.get('cache', {})) if _CACHE_SERVICE_AVAILABLE else None
    
    # Services qui dépendent des services de base
    package_service = PackageService(
        environment_service=environment_service,
        system_service=system_service,
        cache_service=cache_service,
        config=config.get('package', {})
    ) if _PACKAGE_SERVICE_AVAILABLE else None
    
    migration_service = MigrationService(
        system_service=system_service,
        config=config.get('migration', {})
    ) if _MIGRATION_SERVICE_AVAILABLE else None
    
    # Service de diagnostic qui utilise tous les autres
    diagnostic_service = DiagnosticService(
        environment_service=environment_service,
        package_service=package_service,
        system_service=system_service,
        cache_service=cache_service,
        migration_service=migration_service,
        config=config.get('diagnostic', {})
    ) if _DIAGNOSTIC_SERVICE_AVAILABLE else None
    
    return ServiceContainer(
        environment=environment_service,
        package=package_service,
        system=system_service,
        cache=cache_service,
        diagnostic=diagnostic_service,
        migration=migration_service
    )


def get_service_status() -> Dict[str, bool]:
    """
    Retourne le statut de disponibilité de tous les services.
    
    Returns:
        Dict[str, bool]: Statut de chaque service
    """
    return {
        'environment': _ENVIRONMENT_SERVICE_AVAILABLE,
        'package': _PACKAGE_SERVICE_AVAILABLE,
        'system': _SYSTEM_SERVICE_AVAILABLE,
        'cache': _CACHE_SERVICE_AVAILABLE,
        'diagnostic': _DIAGNOSTIC_SERVICE_AVAILABLE,
        'migration': _MIGRATION_SERVICE_AVAILABLE,
    }


# Exports pour compatibilité et facilité d'utilisation
__all__ = [
    # Services individuels
    'EnvironmentService',
    'PackageService', 
    'SystemService',
    'CacheService',
    'DiagnosticService',
    'MigrationService',
    
    # Architecture services
    'ServiceContainer',
    'create_service_container',
    'get_service_status'
]

# Filtrer les exports selon la disponibilité
available_exports = []
if _ENVIRONMENT_SERVICE_AVAILABLE:
    available_exports.append('EnvironmentService')
if _PACKAGE_SERVICE_AVAILABLE:
    available_exports.append('PackageService')
if _SYSTEM_SERVICE_AVAILABLE:
    available_exports.append('SystemService')
if _CACHE_SERVICE_AVAILABLE:
    available_exports.append('CacheService')
if _DIAGNOSTIC_SERVICE_AVAILABLE:
    available_exports.append('DiagnosticService')
if _MIGRATION_SERVICE_AVAILABLE:
    available_exports.append('MigrationService')

# Toujours exporter l'architecture services
available_exports.extend(['ServiceContainer', 'create_service_container', 'get_service_status'])

__all__ = available_exports

# Version du package services
__version__ = "1.1.0"