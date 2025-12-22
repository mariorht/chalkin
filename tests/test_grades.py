"""
Tests for grade endpoints.
"""
import pytest


class TestGrades:
    """Tests for /api/grades endpoints."""
    
    def test_create_grade(self, client, auth_headers, test_gym):
        """Test creating a new grade."""
        response = client.post("/api/grades",
            headers=auth_headers,
            json={
                "gym_id": test_gym.id,
                "label": "Amarillo",
                "color_hex": "#FFFF00",
                "relative_difficulty": 3,
                "order": 1
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["label"] == "Amarillo"
        assert data["color_hex"] == "#FFFF00"
        assert data["relative_difficulty"] == 3
    
    def test_create_grade_invalid_gym(self, client, auth_headers):
        """Test creating grade for non-existent gym."""
        response = client.post("/api/grades",
            headers=auth_headers,
            json={
                "gym_id": 9999,
                "label": "Test",
                "relative_difficulty": 5
            }
        )
        
        assert response.status_code == 404
    
    def test_create_grade_invalid_color(self, client, auth_headers, test_gym):
        """Test creating grade with invalid color hex."""
        response = client.post("/api/grades",
            headers=auth_headers,
            json={
                "gym_id": test_gym.id,
                "label": "Test",
                "color_hex": "invalid",
                "relative_difficulty": 5
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_grade(self, client, test_grades):
        """Test getting a specific grade."""
        grade = test_grades[0]
        response = client.get(f"/api/grades/{grade.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == grade.id
        assert data["label"] == "Verde"
    
    def test_update_grade(self, client, auth_headers, test_grades):
        """Test updating a grade."""
        grade = test_grades[0]
        response = client.patch(f"/api/grades/{grade.id}",
            headers=auth_headers,
            json={"label": "Verde Claro", "relative_difficulty": 1.5}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "Verde Claro"
        assert data["relative_difficulty"] == 1.5
    
    def test_delete_grade(self, client, auth_headers, test_grades):
        """Test deleting a grade."""
        grade = test_grades[0]
        response = client.delete(f"/api/grades/{grade.id}", headers=auth_headers)
        
        assert response.status_code == 204
        
        # Verify deleted
        response = client.get(f"/api/grades/{grade.id}")
        assert response.status_code == 404
    
    def test_create_grades_bulk(self, client, auth_headers, test_gym):
        """Test bulk creating grades."""
        response = client.post("/api/grades/bulk",
            headers=auth_headers,
            json=[
                {"gym_id": test_gym.id, "label": "V0", "relative_difficulty": 1, "order": 0},
                {"gym_id": test_gym.id, "label": "V1", "relative_difficulty": 2, "order": 1},
                {"gym_id": test_gym.id, "label": "V2", "relative_difficulty": 3, "order": 2},
            ]
        )
        
        assert response.status_code == 201
        data = response.json()
        assert len(data) == 3
        labels = [g["label"] for g in data]
        assert "V0" in labels
        assert "V1" in labels
        assert "V2" in labels
