"""
Tests for the admin password reset flow.
"""
import secrets
from datetime import datetime, timedelta

import pytest

from app.core.security import create_access_token, get_password_hash, hash_token
from app.models.password_reset import PasswordResetToken
from app.models.user import User


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    user = User(
        username="admin",
        email="admin@example.com",
        password_hash=get_password_hash("adminpass123"),
        is_admin=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_headers(admin_user):
    """Auth headers for the admin user."""
    token = create_access_token(data={"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {token}"}


class TestAdminAccess:
    """Admin-only endpoints must reject non-admins."""

    def test_me_requires_admin(self, client, auth_headers):
        response = client.get("/api/admin/me", headers=auth_headers)
        assert response.status_code == 403

    def test_search_requires_admin(self, client, auth_headers):
        response = client.get("/api/admin/users", headers=auth_headers)
        assert response.status_code == 403

    def test_generate_requires_admin(self, client, auth_headers, test_user):
        response = client.post(
            f"/api/admin/users/{test_user.id}/password-reset", headers=auth_headers
        )
        assert response.status_code == 403

    def test_search_requires_auth(self, client):
        response = client.get("/api/admin/users")
        assert response.status_code in (401, 403)


class TestAdminSearch:
    def test_admin_me(self, client, admin_headers, admin_user):
        response = client.get("/api/admin/me", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["email"] == admin_user.email
        assert response.json()["is_admin"] is True

    def test_search_by_email(self, client, admin_headers, test_user):
        response = client.get("/api/admin/users?q=test@", headers=admin_headers)
        assert response.status_code == 200
        emails = [u["email"] for u in response.json()]
        assert "test@example.com" in emails

    def test_search_by_username(self, client, admin_headers, test_user):
        response = client.get("/api/admin/users?q=testuser", headers=admin_headers)
        assert response.status_code == 200
        assert any(u["username"] == "testuser" for u in response.json())


class TestPasswordResetFlow:
    def test_generate_reset_link(self, client, admin_headers, test_user):
        response = client.post(
            f"/api/admin/users/{test_user.id}/password-reset", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["token"]
        assert "/reset-password?token=" in data["reset_path"]
        assert "{link}" in data["email_body"]
        assert data["email_subject"]

    def test_generate_for_missing_user(self, client, admin_headers):
        response = client.post(
            "/api/admin/users/99999/password-reset", headers=admin_headers
        )
        assert response.status_code == 404

    def test_reset_changes_password(self, client, admin_headers, test_user):
        gen = client.post(
            f"/api/admin/users/{test_user.id}/password-reset", headers=admin_headers
        ).json()

        response = client.post("/api/auth/reset-password", json={
            "token": gen["token"],
            "new_password": "brandnewpass",
        })
        assert response.status_code == 200

        # Old password no longer works
        old = client.post("/api/auth/login", json={
            "email": "test@example.com", "password": "testpass123"
        })
        assert old.status_code == 401

        # New password works
        new = client.post("/api/auth/login", json={
            "email": "test@example.com", "password": "brandnewpass"
        })
        assert new.status_code == 200

    def test_token_is_single_use(self, client, admin_headers, test_user):
        gen = client.post(
            f"/api/admin/users/{test_user.id}/password-reset", headers=admin_headers
        ).json()

        first = client.post("/api/auth/reset-password", json={
            "token": gen["token"], "new_password": "firstnewpass"
        })
        assert first.status_code == 200

        second = client.post("/api/auth/reset-password", json={
            "token": gen["token"], "new_password": "secondnewpass"
        })
        assert second.status_code == 400

    def test_invalid_token_rejected(self, client):
        response = client.post("/api/auth/reset-password", json={
            "token": "not-a-real-token", "new_password": "whatever123"
        })
        assert response.status_code == 400

    def test_expired_token_rejected(self, client, db, test_user):
        raw = secrets.token_urlsafe(32)
        db.add(PasswordResetToken(
            user_id=test_user.id,
            token_hash=hash_token(raw),
            expires_at=datetime.utcnow() - timedelta(minutes=1),
            used=False,
        ))
        db.commit()

        response = client.post("/api/auth/reset-password", json={
            "token": raw, "new_password": "whatever123"
        })
        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()

    def test_generating_new_link_invalidates_previous(self, client, admin_headers, test_user):
        first = client.post(
            f"/api/admin/users/{test_user.id}/password-reset", headers=admin_headers
        ).json()
        second = client.post(
            f"/api/admin/users/{test_user.id}/password-reset", headers=admin_headers
        ).json()

        stale = client.post("/api/auth/reset-password", json={
            "token": first["token"], "new_password": "whatever123"
        })
        assert stale.status_code == 400

        fresh = client.post("/api/auth/reset-password", json={
            "token": second["token"], "new_password": "whatever123"
        })
        assert fresh.status_code == 200

    def test_existing_jwt_invalidated_after_reset(self, client, admin_headers, test_user, auth_headers):
        # auth_headers holds a token issued before the reset
        before = client.get("/api/auth/me", headers=auth_headers)
        assert before.status_code == 200

        gen = client.post(
            f"/api/admin/users/{test_user.id}/password-reset", headers=admin_headers
        ).json()
        client.post("/api/auth/reset-password", json={
            "token": gen["token"], "new_password": "brandnewpass"
        })

        after = client.get("/api/auth/me", headers=auth_headers)
        assert after.status_code == 401
