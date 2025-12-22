"""
Tests for authentication endpoints.
"""
import pytest


class TestAuth:
    """Tests for /api/auth endpoints."""
    
    def test_register_user(self, client):
        """Test user registration."""
        response = client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "securepass123"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"
        assert "password" not in data
        assert "password_hash" not in data
    
    def test_register_duplicate_email(self, client, test_user):
        """Test registration with existing email fails."""
        response = client.post("/api/auth/register", json={
            "username": "different",
            "email": "test@example.com",  # Same as test_user
            "password": "securepass123"
        })
        
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]
    
    def test_register_duplicate_username(self, client, test_user):
        """Test registration with existing username fails."""
        response = client.post("/api/auth/register", json={
            "username": "testuser",  # Same as test_user
            "email": "different@example.com",
            "password": "securepass123"
        })
        
        assert response.status_code == 400
        assert "Username already taken" in response.json()["detail"]
    
    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "testpass123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password."""
        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent email."""
        response = client.post("/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "anypassword"
        })
        
        assert response.status_code == 401
    
    def test_get_profile(self, client, auth_headers, test_user):
        """Test getting current user profile."""
        response = client.get("/api/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
    
    def test_get_profile_unauthorized(self, client):
        """Test profile access without token."""
        response = client.get("/api/auth/me")
        
        assert response.status_code == 401  # No credentials
    
    def test_update_profile(self, client, auth_headers):
        """Test updating user profile."""
        response = client.patch("/api/auth/me", 
            headers=auth_headers,
            json={"username": "updatedname"}
        )
        
        assert response.status_code == 200
        assert response.json()["username"] == "updatedname"
