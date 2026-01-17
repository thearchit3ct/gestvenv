"""
Dépendances partagées pour l'API FastAPI
"""

from typing import Optional
from functools import lru_cache

from gestvenv.core.environment_manager import EnvironmentManager
from gestvenv.core.config_manager import ConfigManager


@lru_cache()
def get_config_manager() -> ConfigManager:
    """Retourne une instance singleton du ConfigManager"""
    return ConfigManager()


@lru_cache()
def get_environment_manager() -> EnvironmentManager:
    """Retourne une instance singleton de l'EnvironmentManager"""
    config_manager = get_config_manager()
    return EnvironmentManager(config_manager)