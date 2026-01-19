"""
Configuration pytest pour les tests d'intégration GestVenv
"""

import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Crée un répertoire temporaire pour les tests"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def config_manager(temp_dir):
    """ConfigManager configuré pour les tests d'intégration"""
    from gestvenv.core.config_manager import ConfigManager

    config_path = temp_dir / "config.json"
    manager = ConfigManager(config_path)
    return manager


@pytest.fixture
def env_manager(temp_dir, config_manager):
    """
    EnvironmentManager réel pour tests d'intégration.
    Permet d'injecter des mocks via les attributs privés (_cache_service, etc.)
    """
    from gestvenv.core.environment_manager import EnvironmentManager

    manager = EnvironmentManager(config_manager)
    yield manager


@pytest.fixture
def sample_pyproject_toml():
    """Contenu pyproject.toml exemple"""
    return '''[project]
name = "test-project"
version = "0.1.0"
description = "Test project"
requires-python = ">=3.9"
dependencies = [
    "requests>=2.25.0",
    "click>=8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "black>=22.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
'''


@pytest.fixture
def sample_requirements_content():
    """Contenu requirements.txt exemple"""
    return """# Main dependencies
requests>=2.25.0
click>=8.0
flask==2.3.0

# Development
pytest>=7.0  # Testing
black>=22.0
"""
