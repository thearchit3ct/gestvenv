"""
Tests for the main FastAPI application
"""

import pytest


class TestAPIConfiguration:
    """Tests for API configuration without importing the full app"""

    def test_api_module_structure(self):
        """Test that API module structure is correct"""
        import api
        assert hasattr(api, '__init__')

    def test_core_config_exists(self):
        """Test that core config module exists"""
        from api.core import config
        assert hasattr(config, 'settings')

    def test_settings_has_required_attributes(self):
        """Test that settings has required attributes"""
        from api.core.config import settings
        # Check that cors_origins attribute exists
        assert hasattr(settings, 'cors_origins')

    def test_models_module_exists(self):
        """Test that models module exists"""
        import api.models
        assert api.models is not None

    def test_routes_module_exists(self):
        """Test that routes module exists"""
        import api.routes
        assert api.routes is not None


class TestDependencies:
    """Test that required dependencies are available"""

    def test_fastapi_installed(self):
        """Test that FastAPI is installed"""
        import fastapi
        assert fastapi.__version__

    def test_pydantic_installed(self):
        """Test that Pydantic is installed"""
        import pydantic
        assert pydantic.__version__

    def test_websockets_installed(self):
        """Test that websockets is installed"""
        import websockets
        assert websockets.__version__
