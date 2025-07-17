"""
Services métier pour GestVenv v1.1

Ce module contient tous les services de logique métier :
- PackageService : Gestion des packages et dépendances
- CacheService : Cache intelligent et mode hors ligne
- MigrationService : Migration et conversion de formats
- SystemService : Intégration système et commandes
- DiagnosticService : Diagnostic et réparation automatique
- TemplateService : Gestion des templates de projets
"""

from .package_service import PackageService
from .cache_service import CacheService
from .migration_service import MigrationService
from .system_service import SystemService
from .diagnostic_service import DiagnosticService
from .template_service import TemplateService

__all__ = [
    "PackageService",
    "CacheService", 
    "MigrationService",
    "SystemService",
    "DiagnosticService",
    "TemplateService",
]

# Version des services
__version__ = "1.1.0"