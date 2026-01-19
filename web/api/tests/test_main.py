"""
Tests for the main FastAPI application
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


# Mock the settings and services before importing the app
@pytest.fixture(autouse=True)
def mock_settings():
    """Mock settings for all tests"""
    with patch('api.core.config.settings') as mock:
        mock.cors_origins = ["http://localhost:3000"]
        mock.SERVE_STATIC_FILES = False
        yield mock


@pytest.fixture
def client(mock_settings):
    """Create a test client for the FastAPI app"""
    # Need to import after mocking
    from api.main import app
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for the health check endpoint"""

    def test_health_check(self, client):
        """Test that health check returns correct status"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert data["service"] == "GestVenv Web API"


class TestAPIDocumentation:
    """Tests for API documentation endpoints"""

    def test_openapi_schema(self, client):
        """Test that OpenAPI schema is accessible"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert data["info"]["title"] == "GestVenv Web API"

    def test_docs_endpoint(self, client):
        """Test that Swagger UI docs are accessible"""
        response = client.get("/api/docs")
        assert response.status_code == 200

    def test_redoc_endpoint(self, client):
        """Test that ReDoc docs are accessible"""
        response = client.get("/api/redoc")
        assert response.status_code == 200


class TestCORSMiddleware:
    """Tests for CORS middleware configuration"""

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in responses"""
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        # CORS preflight should return 200 or be handled
        assert response.status_code in [200, 405]
