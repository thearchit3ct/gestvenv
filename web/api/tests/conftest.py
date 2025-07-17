"""
Pytest configuration for API tests
"""

import pytest
from unittest.mock import Mock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock services
@pytest.fixture
def mock_environment_service():
    return Mock()

@pytest.fixture
def mock_package_service():
    return Mock()

@pytest.fixture
def mock_cache_service():
    return Mock()

@pytest.fixture
def mock_template_service():
    return Mock()