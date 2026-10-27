"""
Tests for gym endpoints.
"""
import pytest


class TestGyms:
    """Tests for /api/gyms endpoints."""
    
    def test_list_gyms_empty(self, client):
        """Test listing gyms when none exist."""
        response = client.get("/api/gyms")
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_list_gyms(self, client, test_gym):
        """Test listing gyms."""
        response = client.get("/api/gyms")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Climbing Gym"
    
    def test_search_gyms(self, client, test_gym):
        """Test searching gyms by name."""
        response = client.get("/api/gyms?search=Climbing")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        
        # Search for non-existent
        response = client.get("/api/gyms?search=NonExistent")
        assert response.status_code == 200
        assert response.json() == []
    
    def test_create_gym(self, client, auth_headers):
        """Test creating a new gym."""
        response = client.post("/api/gyms",
            headers=auth_headers,
            json={
                "name": "New Gym",
                "location": "New City",
                "grading_system_type": "v-scale"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Gym"
        assert data["grading_system_type"] == "v-scale"
    
    def test_create_gym_unauthorized(self, client):
        """Test creating gym without auth fails."""
        response = client.post("/api/gyms", json={
            "name": "New Gym",
            "location": "New City"
        })
        
        assert response.status_code == 401
    
    def test_get_gym(self, client, test_gym):
        """Test getting a specific gym."""
        response = client.get(f"/api/gyms/{test_gym.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_gym.id
        assert data["name"] == "Test Climbing Gym"
    
    def test_get_gym_not_found(self, client):
        """Test getting non-existent gym."""
        response = client.get("/api/gyms/9999")
        
        assert response.status_code == 404
    
    def test_update_gym(self, client, auth_headers, test_gym):
        """Unverified gyms can be fixed by any authenticated user."""
        response = client.patch(f"/api/gyms/{test_gym.id}",
            headers=auth_headers,
            json={"name": "Updated Gym Name"}
        )
        
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Gym Name"

    def test_new_gym_is_unverified(self, client, auth_headers):
        """A freshly created gym is unverified by default."""
        response = client.post("/api/gyms",
            headers=auth_headers,
            json={"name": "Nuevo", "location": "X"}
        )

        assert response.status_code == 201
        assert response.json()["is_verified"] is False
        assert response.json()["verified_at"] is None

    def test_verified_gym_cannot_be_edited_by_regular_user(
        self, client, db, auth_headers, test_gym
    ):
        """Once verified, a gym is admin-only."""
        test_gym.is_verified = True
        db.commit()

        response = client.patch(f"/api/gyms/{test_gym.id}",
            headers=auth_headers,
            json={"name": "Hackeado"}
        )

        assert response.status_code == 403
        db.refresh(test_gym)
        assert test_gym.name == "Test Climbing Gym"

    def test_admin_can_edit_verified_gym(self, client, db, create_user, test_gym):
        """Admins keep editing verified gyms."""
        admin = create_user(
            username="gym_admin", email="gym_admin@test.com", password="password123"
        )
        admin.is_admin = True
        db.commit()
        login = client.post(
            "/api/auth/login",
            json={"email": "gym_admin@test.com", "password": "password123"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        test_gym.is_verified = True
        db.commit()

        response = client.patch(f"/api/gyms/{test_gym.id}",
            headers=headers,
            json={"name": "Editado por admin"}
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Editado por admin"

    def test_delete_gym_requires_admin(self, client, auth_headers, test_gym):
        """Deleting a gym cascades to its history, so it is admin-only."""
        response = client.delete(f"/api/gyms/{test_gym.id}", headers=auth_headers)
        assert response.status_code == 403

    def test_delete_gym(self, client, db, create_user, test_gym):
        """Test deleting a gym as an admin."""
        admin = create_user(
            username="gym_admin2", email="gym_admin2@test.com", password="password123"
        )
        admin.is_admin = True
        db.commit()
        login = client.post(
            "/api/auth/login",
            json={"email": "gym_admin2@test.com", "password": "password123"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        response = client.delete(f"/api/gyms/{test_gym.id}", headers=headers)
        
        assert response.status_code == 204
        
        # Verify deleted
        response = client.get(f"/api/gyms/{test_gym.id}")
        assert response.status_code == 404

    def test_admin_can_verify_a_gym(self, client, db, create_user, test_gym):
        """The verify endpoint flips the flag and stamps the date."""
        admin = create_user(
            username="gym_admin3", email="gym_admin3@test.com", password="password123"
        )
        admin.is_admin = True
        db.commit()
        login = client.post(
            "/api/auth/login",
            json={"email": "gym_admin3@test.com", "password": "password123"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        response = client.patch(
            f"/api/admin/gyms/{test_gym.id}/verification",
            headers=headers,
            json={"is_verified": True},
        )
        assert response.status_code == 200
        assert response.json()["is_verified"] is True
        assert response.json()["verified_at"] is not None

        # And back again
        response = client.patch(
            f"/api/admin/gyms/{test_gym.id}/verification",
            headers=headers,
            json={"is_verified": False},
        )
        assert response.status_code == 200
        assert response.json()["is_verified"] is False
        assert response.json()["verified_at"] is None

    def test_regular_user_cannot_verify(self, client, auth_headers, test_gym):
        response = client.patch(
            f"/api/admin/gyms/{test_gym.id}/verification",
            headers=auth_headers,
            json={"is_verified": True},
        )
        assert response.status_code == 403
    
    def test_get_gym_grades(self, client, test_gym, test_grades):
        """Test getting grades for a gym."""
        response = client.get(f"/api/gyms/{test_gym.id}/grades")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4
        # Should be ordered by order/difficulty
        labels = [g["label"] for g in data]
        assert labels == ["Verde", "Azul", "Rojo", "Negro"]
