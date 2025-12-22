"""
Tests for ascent endpoints.
"""
import pytest


class TestAscents:
    """Tests for /api/ascents endpoints."""
    
    def test_get_ascent(self, client, auth_headers, test_ascents):
        """Test getting a specific ascent."""
        ascent = test_ascents[0]
        response = client.get(f"/api/ascents/{ascent.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == ascent.id
        assert data["status"] == "flash"
    
    def test_get_ascent_not_found(self, client, auth_headers):
        """Test getting non-existent ascent."""
        response = client.get("/api/ascents/9999", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_update_ascent(self, client, auth_headers, test_ascents):
        """Test updating an ascent."""
        ascent = test_ascents[0]
        response = client.patch(f"/api/ascents/{ascent.id}",
            headers=auth_headers,
            json={
                "status": "send",
                "attempts": 3,
                "notes": "Finally got it!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "send"
        assert data["attempts"] == 3
        assert data["notes"] == "Finally got it!"
    
    def test_update_ascent_change_grade(self, client, auth_headers, test_ascents, test_grades):
        """Test updating ascent to different grade (same gym)."""
        ascent = test_ascents[0]
        new_grade = test_grades[2]  # Different grade, same gym
        
        response = client.patch(f"/api/ascents/{ascent.id}",
            headers=auth_headers,
            json={"grade_id": new_grade.id}
        )
        
        assert response.status_code == 200
        assert response.json()["grade_id"] == new_grade.id
    
    def test_delete_ascent(self, client, auth_headers, test_ascents):
        """Test deleting an ascent."""
        ascent = test_ascents[0]
        response = client.delete(f"/api/ascents/{ascent.id}", headers=auth_headers)
        
        assert response.status_code == 204
        
        # Verify deleted
        response = client.get(f"/api/ascents/{ascent.id}", headers=auth_headers)
        assert response.status_code == 404
