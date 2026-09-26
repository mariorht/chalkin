"""
Tests for home training activities (sessions without a gym).
"""
from datetime import date


class TestHomeActivities:
    """Tests for activity_type home (no gym, no grades, only exercises)."""

    def test_create_home_session_without_gym(self, client, auth_headers):
        response = client.post(
            "/api/sessions",
            headers=auth_headers,
            json={"activity_type": "home", "title": "Fingerboard en casa"},
        )

        assert response.status_code == 201, response.text
        data = response.json()
        assert data["activity_type"] == "home"
        assert data["gym_id"] is None
        assert data["gym_name"] == "Entrenamiento en casa"
        assert data["total_ascents"] == 0

    def test_create_home_session_ignores_gym(self, client, auth_headers, test_gym):
        response = client.post(
            "/api/sessions",
            headers=auth_headers,
            json={"activity_type": "home", "gym_id": test_gym.id},
        )

        assert response.status_code == 201, response.text
        assert response.json()["gym_id"] is None

    def test_gym_activity_requires_gym(self, client, auth_headers):
        response = client.post(
            "/api/sessions",
            headers=auth_headers,
            json={"activity_type": "gym"},
        )

        assert response.status_code == 400

    def test_default_activity_type_is_gym(self, client, auth_headers, test_gym):
        response = client.post(
            "/api/sessions",
            headers=auth_headers,
            json={"gym_id": test_gym.id},
        )

        assert response.status_code == 201, response.text
        assert response.json()["activity_type"] == "gym"

    def test_add_exercise_to_home_session(self, client, auth_headers):
        created = client.post(
            "/api/sessions",
            headers=auth_headers,
            json={"activity_type": "home"},
        ).json()

        response = client.post(
            f"/api/sessions/{created['id']}/exercises",
            headers=auth_headers,
            json={"exercise_type": "fingerboard", "sets": 3, "reps": "7"},
        )

        assert response.status_code == 201, response.text
        assert response.json()["exercise_type"] == "fingerboard"

    def test_cannot_log_ascent_in_home_session(self, client, auth_headers, test_grades):
        created = client.post(
            "/api/sessions",
            headers=auth_headers,
            json={"activity_type": "home"},
        ).json()

        response = client.post(
            f"/api/sessions/{created['id']}/ascents",
            headers=auth_headers,
            json={"grade_id": test_grades[0].id, "status": "send"},
        )

        assert response.status_code == 400

    def test_get_home_session(self, client, auth_headers):
        created = client.post(
            "/api/sessions",
            headers=auth_headers,
            json={"activity_type": "home", "notes": "hangs"},
        ).json()

        response = client.get(f"/api/sessions/{created['id']}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["activity_type"] == "home"
        assert data["gym_id"] is None
        assert data["ascents"] == []
        assert data["date"] == str(date.today())

    def test_list_filter_by_activity_type(self, client, auth_headers, test_gym):
        client.post("/api/sessions", headers=auth_headers, json={"gym_id": test_gym.id})
        client.post("/api/sessions", headers=auth_headers, json={"activity_type": "home"})

        response = client.get("/api/sessions?activity_type=home", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["activity_type"] == "home"

    def test_convert_empty_gym_session_to_home(self, client, auth_headers, test_session):
        response = client.patch(
            f"/api/sessions/{test_session.id}",
            headers=auth_headers,
            json={"activity_type": "home"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["activity_type"] == "home"
        assert data["gym_id"] is None

    def test_cannot_convert_session_with_ascents_to_home(
        self, client, auth_headers, test_session, test_grades
    ):
        client.post(
            f"/api/sessions/{test_session.id}/ascents",
            headers=auth_headers,
            json={"grade_id": test_grades[0].id, "status": "send"},
        )

        response = client.patch(
            f"/api/sessions/{test_session.id}",
            headers=auth_headers,
            json={"activity_type": "home"},
        )

        assert response.status_code == 400

    def test_stats_do_not_crash_with_home_session(self, client, auth_headers):
        client.post("/api/sessions", headers=auth_headers, json={"activity_type": "home"})

        response = client.get("/api/stats/me", headers=auth_headers)

        assert response.status_code == 200, response.text
