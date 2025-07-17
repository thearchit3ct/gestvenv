"""
Dependency injection for FastAPI
"""

from typing import Generator
from ..services.environment_service import EnvironmentService
from ..services.package_service import PackageService
from ..services.cache_service import CacheService
from ..services.template_service import TemplateService

# Service instances
_environment_service = None
_package_service = None
_cache_service = None
_template_service = None


def get_environment_service() -> EnvironmentService:
    """Get environment service instance"""
    global _environment_service
    if _environment_service is None:
        _environment_service = EnvironmentService()
    return _environment_service


def get_package_service() -> PackageService:
    """Get package service instance"""
    global _package_service
    if _package_service is None:
        _package_service = PackageService()
    return _package_service


def get_cache_service() -> CacheService:
    """Get cache service instance"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


def get_template_service() -> TemplateService:
    """Get template service instance"""
    global _template_service
    if _template_service is None:
        _template_service = TemplateService()
    return _template_service