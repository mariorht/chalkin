"""
Tests for main app endpoints.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_serve_index_page():
    """Test that the main page is served."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "Chalkin"


def test_api_docs_available():
    """Test that API docs are available."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_schema():
    """Test that OpenAPI schema is generated."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Chalkin"

