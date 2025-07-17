"""
Module de tests d'intégration pour GestVenv v1.1

Tests des workflows complets et de l'intégration entre composants
"""

import tempfile
import pytest
from pathlib import Path
from gestvenv.core.config_manager import ConfigManager
from gestvenv.core.environment_manager import EnvironmentManager

@pytest.fixture
def temp_home(tmp_path):
    """Répertoire home temporaire pour les tests"""
    gestvenv_dir = tmp_path / ".gestvenv"
    gestvenv_dir.mkdir()
    return tmp_path

@pytest.fixture
def config_manager(temp_home):
    """ConfigManager avec configuration temporaire"""
    config_path = temp_home / ".gestvenv" / "config.json"
    return ConfigManager(config_path)

@pytest.fixture
def env_manager(config_manager):
    """EnvironmentManager pour les tests"""
    return EnvironmentManager(config_manager)

@pytest.fixture
def sample_pyproject_toml():
    """Contenu pyproject.toml de test"""
    return '''[project]
name = "test-project"
version = "0.1.0"
description = "Projet de test"
dependencies = ["requests>=2.25.0", "click>=8.0"]

[project.optional-dependencies]
dev = ["pytest>=6.0", "black>=21.0"]
test = ["pytest-cov>=2.0"]

[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"
'''

@pytest.fixture
def sample_requirements_txt():
    """Contenu requirements.txt de test"""
    return '''requests==2.28.1
click==8.1.3
pytest==7.1.2
black==22.3.0
'''