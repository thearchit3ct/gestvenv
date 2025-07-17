"""
Configuration pytest pour les tests de performance
"""

import pytest


def pytest_configure(config):
    """Configure les marqueurs personnalisés"""
    config.addinivalue_line(
        "markers", "benchmark: marque les tests de performance"
    )


@pytest.fixture(scope="session")
def performance_threshold():
    """Seuils de performance acceptables"""
    return {
        "env_creation": 30.0,  # secondes
        "package_install": 60.0,  # secondes
        "cache_operation": 0.1,  # secondes
        "parsing": 0.1,  # secondes
    }