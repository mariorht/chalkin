"""
Tests for session endpoints.
"""
import pytest
from datetime import date

from app.core.security import create_access_token
from app.models.ascent import Ascent
from app.models.session import Session


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

    def test_session_includes_strava_activity_id(self, client, auth_headers, test_session, db):
        """Uploaded sessions must expose strava_activity_id so the UI can link to it."""
        test_session.strava_activity_id = 123456789
        db.commit()

        detail = client.get(f"/api/sessions/{test_session.id}", headers=auth_headers)
        assert detail.status_code == 200
        assert detail.json()["strava_activity_id"] == 123456789

        listing = client.get("/api/sessions", headers=auth_headers)
        assert listing.status_code == 200
        assert listing.json()[0]["strava_activity_id"] == 123456789
    
    def test_get_session_not_found(self, client, auth_headers):
        """Test getting non-existent session."""
        response = client.get("/api/sessions/9999", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_create_session_with_title(self, client, auth_headers, test_gym):
        """Test creating a session with title and subtitle."""
        response = client.post("/api/sessions",
            headers=auth_headers,
            json={
                "gym_id": test_gym.id,
                "title": "Sesión de fuerza",
                "subtitle": "Trabajando laterales",
                "notes": "Buen día"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Sesión de fuerza"
        assert data["subtitle"] == "Trabajando laterales"
    
    def test_update_session_title(self, client, auth_headers, test_session):
        """Test updating session title and subtitle."""
        response = client.patch(f"/api/sessions/{test_session.id}",
            headers=auth_headers,
            json={
                "title": "Nuevo título",
                "subtitle": "Nuevo subtítulo"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Nuevo título"
        assert data["subtitle"] == "Nuevo subtítulo"
    
    def test_session_includes_gym_location(self, client, auth_headers, test_session):
        """Test that session response includes gym_location."""
        response = client.get("/api/sessions", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        # gym_location should be present (may be None if gym has no location)
        assert "gym_location" in data[0]
    
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

    def test_delete_session_not_found(self, client, auth_headers):
        """Test deleting a session that does not exist."""
        response = client.delete("/api/sessions/9999", headers=auth_headers)

        assert response.status_code == 404

    def test_delete_session_unauthorized(self, client, test_session):
        """Test deleting a session without authentication."""
        response = client.delete(f"/api/sessions/{test_session.id}")

        assert response.status_code == 401

    def test_delete_session_forbidden_for_other_user(
        self, client, db, test_session, create_user
    ):
        """Test that a user cannot delete someone else's session."""
        other = create_user("intruder", "intruder@example.com", "intruderpass123")
        other_token = create_access_token(data={"sub": str(other.id)})
        other_headers = {"Authorization": f"Bearer {other_token}"}

        response = client.delete(
            f"/api/sessions/{test_session.id}", headers=other_headers
        )

        # No se revela que existe: 404 y la sesión sigue intacta
        assert response.status_code == 404

        db.expire_all()
        assert db.query(Session).filter(Session.id == test_session.id).first() is not None

    def test_delete_session_removes_ascents(
        self, client, db, auth_headers, test_session, test_grades
    ):
        """Test that deleting a session also removes its ascents."""
        session_id = test_session.id
        client.post(
            f"/api/sessions/{session_id}/ascents",
            headers=auth_headers,
            json={"grade_id": test_grades[0].id, "status": "flash"},
        )
        client.post(
            f"/api/sessions/{session_id}/ascents",
            headers=auth_headers,
            json={"grade_id": test_grades[1].id, "status": "send"},
        )

        assert db.query(Ascent).filter(Ascent.session_id == session_id).count() == 2

        response = client.delete(f"/api/sessions/{session_id}", headers=auth_headers)
        assert response.status_code == 204

        db.expire_all()
        assert db.query(Ascent).filter(Ascent.session_id == session_id).count() == 0

    def test_delete_session_does_not_affect_other_sessions(
        self, client, db, auth_headers, test_user, test_gym, test_session
    ):
        """Test that deleting one session leaves the user's other sessions untouched."""
        deleted_id = test_session.id
        other = Session(user_id=test_user.id, gym_id=test_gym.id, date=date.today())
        db.add(other)
        db.commit()
        db.refresh(other)
        other_id = other.id

        response = client.delete(f"/api/sessions/{deleted_id}", headers=auth_headers)
        assert response.status_code == 204

        db.expire_all()
        assert db.query(Session).filter(Session.id == other_id).first() is not None

        response = client.get("/api/sessions", headers=auth_headers)
        assert response.status_code == 200
        remaining_ids = [s["id"] for s in response.json()]
        assert other_id in remaining_ids
        assert deleted_id not in remaining_ids

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
