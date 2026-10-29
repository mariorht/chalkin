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
            json={
                "gym_id": test_gym.id,
                "grades": [
                    {"label": "V0", "relative_difficulty": 1, "order": 0},
                    {"label": "V1", "relative_difficulty": 2, "order": 1},
                    {"label": "V2", "relative_difficulty": 3, "order": 2},
                ]
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert len(data) == 3
        labels = [g["label"] for g in data]
        assert "V0" in labels
        assert "V1" in labels
        assert "V2" in labels


class TestGradePermissions:
    """Grades follow the verified-gym rule, and history is protected."""

    def test_can_edit_grades_of_unverified_gym(self, client, auth_headers, test_gym):
        response = client.post(
            "/api/grades",
            headers=auth_headers,
            json={
                "gym_id": test_gym.id,
                "label": "Morado",
                "relative_difficulty": 9,
                "order": 9,
            },
        )
        assert response.status_code == 201

    def test_cannot_edit_grades_of_verified_gym(
        self, client, db, auth_headers, test_gym
    ):
        test_gym.is_verified = True
        db.commit()

        response = client.post(
            "/api/grades",
            headers=auth_headers,
            json={
                "gym_id": test_gym.id,
                "label": "Morado",
                "relative_difficulty": 9,
                "order": 9,
            },
        )
        assert response.status_code == 403

    def test_cannot_update_grade_of_verified_gym(
        self, client, db, auth_headers, test_gym, test_grades
    ):
        test_gym.is_verified = True
        db.commit()

        response = client.patch(
            f"/api/grades/{test_grades[0].id}",
            headers=auth_headers,
            json={"label": "Cambiado"},
        )
        assert response.status_code == 403

    def test_cannot_bulk_create_grades_of_verified_gym(
        self, client, db, auth_headers, test_gym
    ):
        test_gym.is_verified = True
        db.commit()

        response = client.post(
            "/api/grades/bulk",
            headers=auth_headers,
            json={
                "gym_id": test_gym.id,
                "grades": [{"label": "V0", "relative_difficulty": 1, "order": 0}],
            },
        )
        assert response.status_code == 403

    def test_delete_grade_in_use_archives_it(
        self, client, db, auth_headers, test_gym, test_grades, test_session
    ):
        """A grade with history is archived, never deleted."""
        from app.models.ascent import Ascent

        db.add(Ascent(session_id=test_session.id, grade_id=test_grades[0].id))
        db.commit()

        response = client.delete(
            f"/api/grades/{test_grades[0].id}", headers=auth_headers
        )
        assert response.status_code == 204

        db.refresh(test_grades[0])
        assert test_grades[0].is_active is False
        # The ascent survives and still resolves its grade
        assert db.query(Ascent).count() == 1
        assert db.query(Ascent).first().grade.label == test_grades[0].label

    def test_can_delete_unused_grade(self, client, auth_headers, test_gym, test_grades):
        response = client.delete(
            f"/api/grades/{test_grades[0].id}", headers=auth_headers
        )
        assert response.status_code == 204

        # No history: the row is really gone
        assert client.get(f"/api/grades/{test_grades[0].id}").status_code == 404

    def test_archived_grade_cannot_be_used_for_new_ascents(
        self, client, db, auth_headers, test_gym, test_grades, test_session
    ):
        test_grades[0].is_active = False
        db.commit()

        response = client.post(
            f"/api/sessions/{test_session.id}/ascents",
            headers=auth_headers,
            json={"grade_id": test_grades[0].id, "status": "send"},
        )
        assert response.status_code == 400
        assert "archivado" in response.json()["detail"]

    def test_admin_can_restore_archived_grade(
        self, client, db, create_user, test_gym, test_grades
    ):
        admin = create_user(
            username="grade_admin", email="grade_admin@test.com", password="password123"
        )
        admin.is_admin = True
        db.commit()
        login = client.post(
            "/api/auth/login",
            json={"email": "grade_admin@test.com", "password": "password123"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        test_grades[0].is_active = False
        db.commit()

        response = client.post(
            f"/api/grades/{test_grades[0].id}/restore", headers=headers
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is True

    def test_non_admin_cannot_restore_grade(
        self, client, db, auth_headers, test_gym, test_grades
    ):
        test_grades[0].is_active = False
        db.commit()

        response = client.post(
            f"/api/grades/{test_grades[0].id}/restore", headers=auth_headers
        )
        assert response.status_code == 403


class TestGradeDuplicates:
    """A gym cannot hold two grades with the same label."""

    def test_duplicate_label_rejected(self, client, auth_headers, test_gym, test_grades):
        response = client.post(
            "/api/grades",
            headers=auth_headers,
            json={
                "gym_id": test_gym.id,
                "label": test_grades[0].label,
                "relative_difficulty": 9,
                "order": 9,
            },
        )
        assert response.status_code == 409
        assert test_grades[0].label in response.json()["detail"]

    def test_duplicate_ignores_case_and_spaces(
        self, client, auth_headers, test_gym, test_grades
    ):
        response = client.post(
            "/api/grades",
            headers=auth_headers,
            json={
                "gym_id": test_gym.id,
                "label": f"  {test_grades[0].label.upper()}  ",
                "relative_difficulty": 9,
                "order": 9,
            },
        )
        assert response.status_code == 409

    def test_rename_to_existing_label_rejected(
        self, client, auth_headers, test_gym, test_grades
    ):
        response = client.patch(
            f"/api/grades/{test_grades[1].id}",
            headers=auth_headers,
            json={"label": test_grades[0].label},
        )
        assert response.status_code == 409

    def test_bulk_with_repeated_labels_rejected(
        self, client, auth_headers, test_gym
    ):
        response = client.post(
            "/api/grades/bulk",
            headers=auth_headers,
            json={
                "gym_id": test_gym.id,
                "grades": [
                    {"label": "Principiante", "relative_difficulty": 1, "order": 1},
                    {"label": "principiante", "relative_difficulty": 1, "order": 2},
                ],
            },
        )
        assert response.status_code == 400

    def test_creating_a_label_of_an_archived_grade_is_rejected(
        self, client, db, auth_headers, test_gym, test_grades
    ):
        test_grades[0].is_active = False
        db.commit()

        response = client.post(
            "/api/grades",
            headers=auth_headers,
            json={
                "gym_id": test_gym.id,
                "label": test_grades[0].label,
                "relative_difficulty": 9,
                "order": 9,
            },
        )
        assert response.status_code == 409
        assert "archivado" in response.json()["detail"]
