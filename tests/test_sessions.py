"""
Tests for session endpoints.
"""
import pytest
from datetime import date


class TestSessions:
    """Tests for /api/sessions endpoints."""
    
    def test_list_sessions_empty(self, client, auth_headers):
        """Test listing sessions when none exist."""
        response = client.get("/api/sessions", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_create_session(self, client, auth_headers, test_gym):
        """Test creating a new session (check-in)."""
        response = client.post("/api/sessions",
            headers=auth_headers,
            json={
                "gym_id": test_gym.id,
                "notes": "Feeling strong today!"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["gym_id"] == test_gym.id
        assert data["notes"] == "Feeling strong today!"
        assert data["date"] == str(date.today())
    
    def test_create_session_invalid_gym(self, client, auth_headers):
        """Test creating session for non-existent gym."""
        response = client.post("/api/sessions",
            headers=auth_headers,
            json={"gym_id": 9999}
        )
        
        assert response.status_code == 404
    
    def test_list_sessions(self, client, auth_headers, test_session):
        """Test listing user's sessions."""
        response = client.get("/api/sessions", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == test_session.id
    
    def test_list_sessions_filter_by_gym(self, client, auth_headers, test_session, test_gym):
        """Test filtering sessions by gym."""
        response = client.get(f"/api/sessions?gym_id={test_gym.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        
        # Non-existent gym
        response = client.get("/api/sessions?gym_id=9999", headers=auth_headers)
        assert response.json() == []
    
    def test_get_session(self, client, auth_headers, test_session):
        """Test getting a specific session."""
        response = client.get(f"/api/sessions/{test_session.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_session.id
    
    def test_get_session_with_ascents(self, client, auth_headers, test_session, test_ascents):
        """Test getting session with ascent summary."""
        response = client.get(f"/api/sessions/{test_session.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_ascents"] == 4
        assert data["sends"] == 2  # 2 SENDs
        assert data["flashes"] == 1  # 1 FLASH
        assert data["projects"] == 1  # 1 PROJECT
    
    def test_get_session_not_found(self, client, auth_headers):
        """Test getting non-existent session."""
        response = client.get("/api/sessions/9999", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_update_session(self, client, auth_headers, test_session):
        """Test updating a session."""
        response = client.patch(f"/api/sessions/{test_session.id}",
            headers=auth_headers,
            json={"notes": "Updated notes"}
        )
        
        assert response.status_code == 200
        assert response.json()["notes"] == "Updated notes"
    
    def test_end_session(self, client, auth_headers, test_session):
        """Test ending a session."""
        response = client.post(f"/api/sessions/{test_session.id}/end", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["ended_at"] is not None
    
    def test_delete_session(self, client, auth_headers, test_session):
        """Test deleting a session."""
        response = client.delete(f"/api/sessions/{test_session.id}", headers=auth_headers)
        
        assert response.status_code == 204
        
        # Verify deleted
        response = client.get(f"/api/sessions/{test_session.id}", headers=auth_headers)
        assert response.status_code == 404
    
    def test_add_ascent_to_session(self, client, auth_headers, test_session, test_grades):
        """Test adding an ascent to a session."""
        response = client.post(f"/api/sessions/{test_session.id}/ascents",
            headers=auth_headers,
            json={
                "grade_id": test_grades[0].id,
                "status": "flash"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["grade_id"] == test_grades[0].id
        assert data["status"] == "flash"
        assert data["session_id"] == test_session.id
    
    def test_add_ascent_wrong_gym_grade(self, client, auth_headers, test_session, db):
        """Test that adding ascent with grade from different gym fails."""
        from app.models.gym import Gym
        from app.models.grade import Grade
        
        # Create another gym with its own grade
        other_gym = Gym(name="Other Gym", location="Other City")
        db.add(other_gym)
        db.commit()
        
        other_grade = Grade(gym_id=other_gym.id, label="Other", relative_difficulty=5)
        db.add(other_grade)
        db.commit()
        
        response = client.post(f"/api/sessions/{test_session.id}/ascents",
            headers=auth_headers,
            json={
                "grade_id": other_grade.id,
                "status": "send"
            }
        )
        
        assert response.status_code == 400
        assert "does not belong to the session's gym" in response.json()["detail"]
    
    def test_list_session_ascents(self, client, auth_headers, test_session, test_ascents):
        """Test listing all ascents in a session."""
        response = client.get(f"/api/sessions/{test_session.id}/ascents", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4
