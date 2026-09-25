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


def test_serve_sense_page():
    """Test that the Chalkin Sense test-lab page is served."""
    response = client.get("/sense")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert "/static/sdk/js/index.js" in response.text


def test_sense_sdk_is_served():
    """Test that the vendored Chalkin Sense SDK modules are served as JS."""
    for name in ("index.js", "protocol.js", "metrics.js", "client.js"):
        response = client.get(f"/static/sdk/js/{name}")
        assert response.status_code == 200, name
        assert "javascript" in response.headers["content-type"], name

    protocol = client.get("/static/sdk/js/protocol.js")
    assert "PROTOCOL_VERSION" in protocol.text

