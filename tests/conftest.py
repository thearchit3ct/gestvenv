"""
Configuration pytest et fixtures partagées pour GestVenv
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock
from click.testing import CliRunner


@pytest.fixture
def temp_dir():
    """Crée un répertoire temporaire pour les tests"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def cli_runner():
    """Runner Click pour tests CLI"""
    return CliRunner()


@pytest.fixture
def config_manager(temp_dir):
    """ConfigManager configuré pour les tests"""
    from gestvenv.core.config_manager import ConfigManager

    config_path = temp_dir / "config.json"
    manager = ConfigManager(config_path)
    return manager


@pytest.fixture
def env_manager(temp_dir, config_manager):
    """EnvironmentManager mock pour tests d'intégration"""
    mock_manager = MagicMock()

    # Configuration des méthodes mockeés
    mock_env_result = MagicMock()
    mock_env_result.success = True
    mock_env_result.environment = MagicMock()
    mock_env_result.environment.name = "test_env"
    mock_env_result.environment.path = temp_dir / "environments" / "test_env"
    mock_env_result.environment.python_version = "3.11"
    mock_env_result.environment.packages = []

    mock_manager.create_environment.return_value = mock_env_result
    mock_manager.create_from_pyproject.return_value = mock_env_result
    mock_manager.get_environment_info.return_value = mock_env_result.environment
    mock_manager.sync_environment.return_value = MagicMock(success=True)
    mock_manager.list_environments.return_value = []

    # Package service mock
    mock_package_service = MagicMock()
    mock_install_result = MagicMock()
    mock_install_result.success = True
    mock_install_result.package_info = MagicMock(name="requests", version="2.31.0")
    mock_install_result.packages_info = []

    mock_package_service.install_package.return_value = mock_install_result
    mock_package_service.install_packages.return_value = mock_install_result
    mock_package_service.update_package.return_value = mock_install_result
    mock_package_service.remove_package.return_value = MagicMock(success=True)

    mock_manager.package_service = mock_package_service

    return mock_manager


@pytest.fixture
def mock_backend():
    """Backend mock pour tests"""
    mock = MagicMock()
    mock.is_available.return_value = True
    mock.create_environment.return_value = MagicMock(success=True)
    mock.install_packages.return_value = MagicMock(success=True)
    return mock


@pytest.fixture
def sample_pyproject_content():
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

# Optional
-e git+https://github.com/example/repo.git#egg=example
"""
