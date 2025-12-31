"""
Tests for authentication endpoints.
"""
import pytest


class TestAuth:
    """Tests for /api/auth endpoints."""
    
    def test_register_user(self, client, test_invitation):
        """Test user registration."""
        response = client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "securepass123",
            "invitation_token": test_invitation.token
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"
        assert "password" not in data
        assert "password_hash" not in data
    
    def test_register_duplicate_email(self, client, test_user, test_invitation):
        """Test registration with existing email fails."""
        response = client.post("/api/auth/register", json={
            "username": "different",
            "email": "test@example.com",  # Same as test_user
            "password": "securepass123",
            "invitation_token": test_invitation.token
        })
        
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]
    
    def test_register_duplicate_username(self, client, test_user, test_invitation):
        """Test registration with existing username fails."""
        response = client.post("/api/auth/register", json={
            "username": "testuser",  # Same as test_user
            "email": "different@example.com",
            "password": "securepass123",
            "invitation_token": test_invitation.token
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


class TestProfilePicture:
    """Tests for profile picture upload/delete."""
    
    def test_upload_profile_picture(self, client, auth_headers):
        """Test uploading a profile picture."""
        # Create a fake image file
        from io import BytesIO
        fake_image = BytesIO(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)  # Minimal PNG header
        fake_image.name = 'test.png'
        
        response = client.post(
            "/api/auth/me/picture",
            headers=auth_headers,
            files={"file": ("test.png", fake_image, "image/png")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["profile_picture"] is not None
        assert "/data/uploads/profiles/" in data["profile_picture"]
    
    def test_upload_invalid_file_type(self, client, auth_headers):
        """Test uploading non-image file fails."""
        from io import BytesIO
        fake_file = BytesIO(b'not an image')
        
        response = client.post(
            "/api/auth/me/picture",
            headers=auth_headers,
            files={"file": ("test.txt", fake_file, "text/plain")}
        )
        
        assert response.status_code == 400
        assert "image" in response.json()["detail"].lower()
    
    def test_delete_profile_picture(self, client, auth_headers):
        """Test deleting profile picture."""
        # First upload a picture
        from io import BytesIO
        fake_image = BytesIO(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
        
        client.post(
            "/api/auth/me/picture",
            headers=auth_headers,
            files={"file": ("test.png", fake_image, "image/png")}
        )
        
        # Now delete it
        response = client.delete("/api/auth/me/picture", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json()["profile_picture"] is None
    
    def test_delete_nonexistent_picture(self, client, auth_headers):
        """Test deleting when no picture exists."""
        response = client.delete("/api/auth/me/picture", headers=auth_headers)
        
        # Should succeed even if no picture
        assert response.status_code == 200
    
    def test_profile_picture_in_login_response(self, client, test_user, db):
        """Test that profile_picture is included in login response."""
        # Set a profile picture directly
        test_user.profile_picture = "/data/uploads/profiles/test.png"
        db.commit()
        db.refresh(test_user)
        
        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "testpass123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        # Check that profile_picture key exists in user object
        assert "profile_picture" in data["user"]
        assert data["user"]["profile_picture"] == "/data/uploads/profiles/test.png"


class TestInvitations:
    """Tests for invitation system."""
    
    def test_register_without_invitation(self, client):
        """Test registration without invitation token fails."""
        response = client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "securepass123"
        })
        
        assert response.status_code == 400
        assert "Invitation token is required" in response.json()["detail"]
    
    def test_register_with_invalid_invitation(self, client):
        """Test registration with invalid invitation token fails."""
        response = client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "securepass123",
            "invitation_token": "invalid_token_123"
        })
        
        assert response.status_code == 400
        assert "Invalid invitation token" in response.json()["detail"]
    
    def test_register_with_used_invitation(self, client, test_user, create_invitation):
        """Test registration with already used invitation fails."""
        used_invitation = create_invitation(test_user.id, used=True)
        
        response = client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "securepass123",
            "invitation_token": used_invitation.token
        })
        
        assert response.status_code == 400
        assert "already been used" in response.json()["detail"]
    
    def test_register_with_expired_invitation(self, client, test_user, create_invitation):
        """Test registration with expired invitation fails."""
        expired_invitation = create_invitation(test_user.id, expired=True)
        
        response = client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "securepass123",
            "invitation_token": expired_invitation.token
        })
        
        assert response.status_code == 400
        assert "expired" in response.json()["detail"]
    
    def test_generate_invitation(self, client, auth_headers):
        """Test generating an invitation."""
        response = client.post("/api/invitations/generate", headers=auth_headers, json={})
        
        assert response.status_code == 201
        data = response.json()
        assert "token" in data
        assert "expires_at" in data
        assert "link" in data
        assert "/register?invitation=" in data["link"]
    
    def test_validate_invitation(self, client, test_invitation):
        """Test validating a valid invitation."""
        response = client.get(f"/api/invitations/validate/{test_invitation.token}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
    
    def test_validate_nonexistent_invitation(self, client):
        """Test validating non-existent invitation."""
        response = client.get("/api/invitations/validate/nonexistent_token")
        
        assert response.status_code == 404
    
    def test_get_my_invitations(self, client, auth_headers, test_user, create_invitation):
        """Test getting user's created invitations."""
        # Create some invitations
        create_invitation(test_user.id)
        create_invitation(test_user.id, used=True)
        
        response = client.get("/api/invitations/my-invitations", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

