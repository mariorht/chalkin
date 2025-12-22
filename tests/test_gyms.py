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
        """Test updating a gym."""
        response = client.patch(f"/api/gyms/{test_gym.id}",
            headers=auth_headers,
            json={"name": "Updated Gym Name"}
        )
        
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Gym Name"
    
    def test_delete_gym(self, client, auth_headers, test_gym):
        """Test deleting a gym."""
        response = client.delete(f"/api/gyms/{test_gym.id}", headers=auth_headers)
        
        assert response.status_code == 204
        
        # Verify deleted
        response = client.get(f"/api/gyms/{test_gym.id}")
        assert response.status_code == 404
    
    def test_get_gym_grades(self, client, test_gym, test_grades):
        """Test getting grades for a gym."""
        response = client.get(f"/api/gyms/{test_gym.id}/grades")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4
        # Should be ordered by order/difficulty
        labels = [g["label"] for g in data]
        assert labels == ["Verde", "Azul", "Rojo", "Negro"]
