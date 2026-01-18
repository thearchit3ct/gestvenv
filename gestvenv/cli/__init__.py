"""
GestVenv CLI Module

Ce module expose l'interface CLI de GestVenv.
Les commandes sont définies dans cli_main.py.
"""

def main():
    """Point d'entrée principal pour la CLI"""
    from gestvenv.cli_main import main as _main
    return _main()

def get_cli():
    """Obtenir l'objet CLI click"""
    from gestvenv.cli_main import cli
    return cli

def __getattr__(name):
    """Import différé pour éviter les imports circulaires.

    Cette fonction permet d'accéder à tous les attributs de cli_main
    via gestvenv.cli, ce qui est nécessaire pour le mocking dans les tests.
    """
    # Imports directs depuis cli_main
    if name in ('cli', 'setup_logging', 'console', '__version__',
                'load_environment_variables', 'list_environments'):
        import gestvenv.cli_main as cli_main
        return getattr(cli_main, name)

    # Re-exports des imports de cli_main pour permettre le mocking
    if name == 'EnvironmentManager':
        from gestvenv.core.environment_manager import EnvironmentManager
        return EnvironmentManager

    if name == 'BackendManager':
        from gestvenv.backends.backend_manager import BackendManager
        return BackendManager

    if name == 'DiagnosticService':
        from gestvenv.services.diagnostic_service import DiagnosticService
        return DiagnosticService

    if name == 'TemplateService':
        from gestvenv.services.template_service import TemplateService
        return TemplateService

    if name == 'MigrationService':
        from gestvenv.services.migration_service import MigrationService
        return MigrationService

    if name == 'CacheService':
        from gestvenv.services.cache_service import CacheService
        return CacheService

    if name == 'GestVenvError':
        from gestvenv.core.exceptions import GestVenvError
        return GestVenvError

    if name in ('ExportFormat', 'BackendType'):
        from gestvenv.core import models
        return getattr(models, name)

    if name == 'logging':
        import logging
        return logging

    if name == 'TomlHandler':
        from gestvenv.utils.toml_handler import TomlHandler
        return TomlHandler

    if name == 'PathUtils':
        from gestvenv.utils.path_utils import PathUtils
        return PathUtils

    raise AttributeError(f"module 'gestvenv.cli' has no attribute '{name}'")

__all__ = [
    'main', 'get_cli', 'cli', 'setup_logging',
    'EnvironmentManager', 'BackendManager',
    'DiagnosticService', 'TemplateService', 'MigrationService', 'CacheService',
    'GestVenvError', 'ExportFormat', 'BackendType',
    'logging', 'TomlHandler', 'PathUtils'
]
