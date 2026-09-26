"""
Tests for Chalkin Sense reps attached to session exercises.
"""
from app.models.user import User
from app.core.security import get_password_hash


def _create_exercise(client, headers, session_id, **extra):
    payload = {"exercise_type": "fingerboard", **extra}
    response = client.post(
        f"/api/sessions/{session_id}/exercises", headers=headers, json=payload
    )
    assert response.status_code == 201, response.text
    return response.json()


def _other_user_headers(client, db):
    other = User(
        username="repvisitor",
        email="repvisitor@example.com",
        password_hash=get_password_hash("otherpass123"),
    )
    db.add(other)
    db.commit()
    login = client.post(
        "/api/auth/login",
        json={"email": "repvisitor@example.com", "password": "otherpass123"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


TWO_REPS = [
    {
        "set_index": 1,
        "rep_index": 1,
        "peak_force_kg": 42.5,
        "mean_force_kg": 30.1,
        "rfd_kg_s": 210.0,
        "tut_s": 7.0,
        "duration_s": 7.4,
    },
    {
        "set_index": 1,
        "rep_index": 2,
        "peak_force_kg": 40.0,
        "mean_force_kg": 28.0,
        "rfd_kg_s": 190.0,
        "tut_s": 6.8,
        "duration_s": 7.1,
    },
]


class TestSenseReps:
    def test_add_reps_bulk(self, client, test_session, auth_headers):
        exercise = _create_exercise(client, auth_headers, test_session.id)

        response = client.post(
            f"/api/sessions/exercises/{exercise['id']}/reps",
            headers=auth_headers,
            json=TWO_REPS,
        )

        assert response.status_code == 201, response.text
        data = response.json()
        assert len(data) == 2
        assert data[0]["peak_force_kg"] == 42.5
        assert data[0]["session_id"] == test_session.id
        assert data[0]["source"] == "sense"

    def test_session_detail_includes_reps(self, client, test_session, auth_headers):
        exercise = _create_exercise(client, auth_headers, test_session.id)
        client.post(
            f"/api/sessions/exercises/{exercise['id']}/reps",
            headers=auth_headers,
            json=TWO_REPS,
        )

        response = client.get(f"/api/sessions/{test_session.id}", headers=auth_headers)

        assert response.status_code == 200
        exercises = response.json()["exercises"]
        assert len(exercises) == 1
        assert len(exercises[0]["sense_reps"]) == 2

    def test_list_reps(self, client, test_session, auth_headers):
        exercise = _create_exercise(client, auth_headers, test_session.id)
        client.post(
            f"/api/sessions/exercises/{exercise['id']}/reps",
            headers=auth_headers,
            json=TWO_REPS,
        )

        response = client.get(
            f"/api/sessions/exercises/{exercise['id']}/reps", headers=auth_headers
        )

        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_delete_rep(self, client, test_session, auth_headers):
        exercise = _create_exercise(client, auth_headers, test_session.id)
        created = client.post(
            f"/api/sessions/exercises/{exercise['id']}/reps",
            headers=auth_headers,
            json=TWO_REPS,
        ).json()

        response = client.delete(f"/api/sessions/reps/{created[0]['id']}", headers=auth_headers)

        assert response.status_code == 204
        remaining = client.get(
            f"/api/sessions/exercises/{exercise['id']}/reps", headers=auth_headers
        ).json()
        assert len(remaining) == 1

    def test_other_user_cannot_add_reps(self, client, db, test_session, auth_headers):
        exercise = _create_exercise(client, auth_headers, test_session.id)
        other_headers = _other_user_headers(client, db)

        response = client.post(
            f"/api/sessions/exercises/{exercise['id']}/reps",
            headers=other_headers,
            json=TWO_REPS,
        )

        assert response.status_code == 403

    def test_other_user_cannot_list_reps(self, client, db, test_session, auth_headers):
        exercise = _create_exercise(client, auth_headers, test_session.id)
        client.post(
            f"/api/sessions/exercises/{exercise['id']}/reps",
            headers=auth_headers,
            json=TWO_REPS,
        )
        other_headers = _other_user_headers(client, db)

        response = client.get(
            f"/api/sessions/exercises/{exercise['id']}/reps", headers=other_headers
        )

        assert response.status_code == 403

    def test_exercise_context_fields(self, client, test_session, auth_headers):
        exercise = _create_exercise(
            client,
            auth_headers,
            test_session.id,
            exercise_type="block",
            protocol="5s max",
            edge_depth_mm=20,
            hand="left",
            grip="pinch",
            added_weight_kg=5.0,
            body_weight_kg=70.0,
        )

        assert exercise["exercise_type"] == "block"
        assert exercise["protocol"] == "5s max"
        assert exercise["edge_depth_mm"] == 20
        assert exercise["hand"] == "left"
        assert exercise["grip"] == "pinch"
        assert exercise["added_weight_kg"] == 5.0
