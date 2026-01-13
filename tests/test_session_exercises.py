"""
Tests for session exercises endpoints.
"""
import pytest
from datetime import date


class TestSessionExercises:
    """Test session exercises functionality."""
    
    def test_create_exercise_pullups(self, client, test_user, test_gym, test_session, auth_headers):
        """Test creating a pullups exercise."""
        response = client.post(
            f"/api/sessions/{test_session.id}/exercises",
            json={
                "exercise_type": "pullups",
                "sets": 3,
                "reps": "10",
                "weight": None,
                "notes": "Felt strong today"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["exercise_type"] == "pullups"
        assert data["sets"] == 3
        assert data["reps"] == "10"
        assert data["weight"] is None
        assert data["notes"] == "Felt strong today"
        assert data["session_id"] == test_session.id
        assert "id" in data
        assert "created_at" in data
    
    def test_create_exercise_campus(self, client, test_user, test_gym, test_session, auth_headers):
        """Test creating a campus exercise."""
        response = client.post(
            f"/api/sessions/{test_session.id}/exercises",
            json={
                "exercise_type": "campus",
                "sets": 5,
                "reps": "1-4-7",
                "notes": "Campus board progression"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["exercise_type"] == "campus"
        assert data["sets"] == 5
        assert data["reps"] == "1-4-7"
    
    def test_create_exercise_weighted(self, client, test_user, test_gym, test_session, auth_headers):
        """Test creating a weighted exercise."""
        response = client.post(
            f"/api/sessions/{test_session.id}/exercises",
            json={
                "exercise_type": "pullups",
                "sets": 3,
                "reps": "8",
                "weight": 10.5,
                "notes": "Added weight for first time"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["weight"] == 10.5
    
    def test_create_exercise_minimal(self, client, test_user, test_gym, test_session, auth_headers):
        """Test creating an exercise with minimal data."""
        response = client.post(
            f"/api/sessions/{test_session.id}/exercises",
            json={
                "exercise_type": "fingerboard"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["exercise_type"] == "fingerboard"
        assert data["sets"] is None
        assert data["reps"] is None
        assert data["weight"] is None
        assert data["notes"] is None
    
    def test_create_exercise_custom_type(self, client, test_user, test_gym, test_session, auth_headers):
        """Test creating a custom exercise type."""
        response = client.post(
            f"/api/sessions/{test_session.id}/exercises",
            json={
                "exercise_type": "core_workout",
                "sets": 3,
                "reps": "30s plank",
                "notes": "Core strengthening"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["exercise_type"] == "core_workout"
    
    def test_create_exercise_invalid_session(self, client, test_user, auth_headers):
        """Test creating exercise for non-existent session."""
        response = client.post(
            "/api/sessions/9999/exercises",
            json={
                "exercise_type": "pullups",
                "sets": 3
            },
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_create_exercise_other_user_session(self, client, test_user, test_gym, test_session, db):
        """Test cannot create exercise in another user's session."""
        from app.models.user import User
        from app.core.security import get_password_hash
        
        # Create another user
        other_user = User(
            username="otheruser",
            email="other@example.com",
            password_hash=get_password_hash("password123")
        )
        db.add(other_user)
        db.commit()
        
        # Login as other user
        login_response = client.post("/api/auth/login", json={
            "email": "other@example.com",
            "password": "password123"
        })
        other_token = login_response.json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}
        
        # Try to add exercise to test_user's session
        response = client.post(
            f"/api/sessions/{test_session.id}/exercises",
            json={
                "exercise_type": "pullups",
                "sets": 3
            },
            headers=other_headers
        )
        
        assert response.status_code == 403
    
    def test_list_exercises_empty(self, client, test_user, test_gym, test_session, auth_headers):
        """Test listing exercises for session with no exercises."""
        response = client.get(
            f"/api/sessions/{test_session.id}/exercises",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_list_exercises(self, client, test_user, test_gym, test_session, auth_headers):
        """Test listing exercises for a session."""
        # Create multiple exercises
        exercises_data = [
            {"exercise_type": "pullups", "sets": 3, "reps": "10"},
            {"exercise_type": "campus", "sets": 5, "reps": "1-4-7"},
            {"exercise_type": "fingerboard", "notes": "20mm edge hangs"}
        ]
        
        for ex_data in exercises_data:
            client.post(
                f"/api/sessions/{test_session.id}/exercises",
                json=ex_data,
                headers=auth_headers
            )
        
        # List exercises
        response = client.get(
            f"/api/sessions/{test_session.id}/exercises",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["exercise_type"] == "pullups"
        assert data[1]["exercise_type"] == "campus"
        assert data[2]["exercise_type"] == "fingerboard"
    
    def test_list_exercises_other_user_cannot_view(self, client, test_user, test_gym, test_session, auth_headers, db):
        """Test other users cannot view exercises unless they are friends."""
        from app.models.user import User
        from app.core.security import get_password_hash
        
        # Create exercise
        client.post(
            f"/api/sessions/{test_session.id}/exercises",
            json={"exercise_type": "pullups", "sets": 3},
            headers=auth_headers
        )
        
        # Create another user
        other_user = User(
            username="otheruser",
            email="other@example.com",
            password_hash=get_password_hash("password123")
        )
        db.add(other_user)
        db.commit()
        
        # Login as other user
        login_response = client.post("/api/auth/login", json={
            "email": "other@example.com",
            "password": "password123"
        })
        other_token = login_response.json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}
        
        # Try to view exercises
        response = client.get(
            f"/api/sessions/{test_session.id}/exercises",
            headers=other_headers
        )
        
        assert response.status_code == 403
    
    def test_update_exercise(self, client, test_user, test_gym, test_session, auth_headers):
        """Test updating an exercise."""
        # Create exercise
        create_response = client.post(
            f"/api/sessions/{test_session.id}/exercises",
            json={
                "exercise_type": "pullups",
                "sets": 3,
                "reps": "10",
                "notes": "Initial note"
            },
            headers=auth_headers
        )
        exercise_id = create_response.json()["id"]
        
        # Update exercise
        response = client.put(
            f"/api/sessions/exercises/{exercise_id}",
            json={
                "sets": 4,
                "reps": "12",
                "weight": 5.0,
                "notes": "Updated note - added weight"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["sets"] == 4
        assert data["reps"] == "12"
        assert data["weight"] == 5.0
        assert data["notes"] == "Updated note - added weight"
        assert data["exercise_type"] == "pullups"  # Type should not change
    
    def test_update_exercise_partial(self, client, test_user, test_gym, test_session, auth_headers):
        """Test partial update of exercise."""
        # Create exercise
        create_response = client.post(
            f"/api/sessions/{test_session.id}/exercises",
            json={
                "exercise_type": "pullups",
                "sets": 3,
                "reps": "10",
                "notes": "Original note"
            },
            headers=auth_headers
        )
        exercise_id = create_response.json()["id"]
        
        # Update only sets
        response = client.put(
            f"/api/sessions/exercises/{exercise_id}",
            json={"sets": 5},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["sets"] == 5
        assert data["reps"] == "10"  # Should remain unchanged
        assert data["notes"] == "Original note"  # Should remain unchanged
    
    def test_update_exercise_not_found(self, client, test_user, auth_headers):
        """Test updating non-existent exercise."""
        response = client.put(
            "/api/sessions/exercises/9999",
            json={"sets": 5},
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_update_exercise_other_user(self, client, test_user, test_gym, test_session, auth_headers, db):
        """Test cannot update another user's exercise."""
        from app.models.user import User
        from app.core.security import get_password_hash
        
        # Create exercise
        create_response = client.post(
            f"/api/sessions/{test_session.id}/exercises",
            json={"exercise_type": "pullups", "sets": 3},
            headers=auth_headers
        )
        exercise_id = create_response.json()["id"]
        
        # Create another user
        other_user = User(
            username="otheruser",
            email="other@example.com",
            password_hash=get_password_hash("password123")
        )
        db.add(other_user)
        db.commit()
        
        # Login as other user
        login_response = client.post("/api/auth/login", json={
            "email": "other@example.com",
            "password": "password123"
        })
        other_token = login_response.json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}
        
        # Try to update exercise
        response = client.put(
            f"/api/sessions/exercises/{exercise_id}",
            json={"sets": 10},
            headers=other_headers
        )
        
        assert response.status_code == 403
    
    def test_delete_exercise(self, client, test_user, test_gym, test_session, auth_headers):
        """Test deleting an exercise."""
        # Create exercise
        create_response = client.post(
            f"/api/sessions/{test_session.id}/exercises",
            json={"exercise_type": "pullups", "sets": 3},
            headers=auth_headers
        )
        exercise_id = create_response.json()["id"]
        
        # Delete exercise
        response = client.delete(
            f"/api/sessions/exercises/{exercise_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204
        
        # Verify it's deleted
        list_response = client.get(
            f"/api/sessions/{test_session.id}/exercises",
            headers=auth_headers
        )
        exercises = list_response.json()
        assert len(exercises) == 0
    
    def test_delete_exercise_not_found(self, client, test_user, auth_headers):
        """Test deleting non-existent exercise."""
        response = client.delete(
            "/api/sessions/exercises/9999",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_delete_exercise_other_user(self, client, test_user, test_gym, test_session, auth_headers, db):
        """Test cannot delete another user's exercise."""
        from app.models.user import User
        from app.core.security import get_password_hash
        
        # Create exercise
        create_response = client.post(
            f"/api/sessions/{test_session.id}/exercises",
            json={"exercise_type": "pullups", "sets": 3},
            headers=auth_headers
        )
        exercise_id = create_response.json()["id"]
        
        # Create another user
        other_user = User(
            username="otheruser",
            email="other@example.com",
            password_hash=get_password_hash("password123")
        )
        db.add(other_user)
        db.commit()
        
        # Login as other user
        login_response = client.post("/api/auth/login", json={
            "email": "other@example.com",
            "password": "password123"
        })
        other_token = login_response.json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}
        
        # Try to delete exercise
        response = client.delete(
            f"/api/sessions/exercises/{exercise_id}",
            headers=other_headers
        )
        
        assert response.status_code == 403
    
    def test_session_with_exercises_in_response(self, client, test_user, test_gym, test_session, auth_headers):
        """Test that exercises are included in session detail response."""
        # Create exercises
        client.post(
            f"/api/sessions/{test_session.id}/exercises",
            json={"exercise_type": "pullups", "sets": 3, "reps": "10"},
            headers=auth_headers
        )
        client.post(
            f"/api/sessions/{test_session.id}/exercises",
            json={"exercise_type": "campus", "sets": 5},
            headers=auth_headers
        )
        
        # Get session detail
        response = client.get(
            f"/api/sessions/{test_session.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "exercises" in data
        assert len(data["exercises"]) == 2
        assert data["exercises"][0]["exercise_type"] == "pullups"
        assert data["exercises"][1]["exercise_type"] == "campus"
    
    def test_exercises_cascade_delete_with_session(self, client, test_user, test_gym, test_session, auth_headers, db):
        """Test that exercises are deleted when session is deleted."""
        from app.models.session_exercise import SessionExercise
        
        # Create exercise
        create_response = client.post(
            f"/api/sessions/{test_session.id}/exercises",
            json={"exercise_type": "pullups", "sets": 3},
            headers=auth_headers
        )
        exercise_id = create_response.json()["id"]
        
        # Verify exercise exists
        exercise = db.query(SessionExercise).filter(SessionExercise.id == exercise_id).first()
        assert exercise is not None
        
        # Delete session
        client.delete(f"/api/sessions/{test_session.id}", headers=auth_headers)
        
        # Verify exercise is also deleted (cascade)
        exercise = db.query(SessionExercise).filter(SessionExercise.id == exercise_id).first()
        assert exercise is None
