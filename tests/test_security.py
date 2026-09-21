"""
Tests for security-related configuration and OAuth state handling.
"""
from urllib.parse import unquote

import pytest

from app.core.config import Settings
from app.core.security import create_oauth_state, verify_oauth_state


class TestSecretKeyValidation:
    """SECRET_KEY must be strong outside debug mode (A1)."""

    def test_placeholder_secret_rejected_in_production(self):
        with pytest.raises(Exception):
            Settings(
                debug=False,
                secret_key="your-secret-key-change-in-production",
                _env_file=None,
            )

    def test_empty_secret_rejected_in_production(self):
        with pytest.raises(Exception):
            Settings(debug=False, secret_key="", _env_file=None)

    def test_placeholder_secret_allowed_in_debug(self):
        settings = Settings(
            debug=True,
            secret_key="your-secret-key-change-in-production",
            _env_file=None,
        )
        assert settings.debug is True

    def test_strong_secret_allowed_in_production(self):
        settings = Settings(debug=False, secret_key="a" * 64, _env_file=None)
        assert settings.secret_key == "a" * 64


class TestOAuthState:
    """Signed OAuth state must be unpredictable and tamper-proof (A2)."""

    def test_roundtrip(self):
        state = create_oauth_state(42)
        assert state != "42"
        assert verify_oauth_state(state) == 42

    def test_tampered_signature_rejected(self):
        state = create_oauth_state(42)
        body, _, signature = state.partition(".")
        flipped = "A" if signature[0] != "A" else "B"
        assert verify_oauth_state(f"{body}.{flipped}{signature[1:]}") is None

    def test_tampered_body_rejected(self):
        state = create_oauth_state(42)
        _, _, signature = state.partition(".")
        forged_body = create_oauth_state(1).partition(".")[0]
        assert verify_oauth_state(f"{forged_body}.{signature}") is None

    def test_expired_state_rejected(self):
        assert verify_oauth_state(create_oauth_state(42, ttl_seconds=-1)) is None

    def test_garbage_state_rejected(self):
        assert verify_oauth_state("not-a-valid-state") is None


class TestSecurityHeaders:
    def test_security_headers_present(self, client):
        response = client.get("/health")
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]

    def test_cors_rejects_unknown_origin(self, client):
        response = client.get("/health", headers={"Origin": "https://evil.example"})
        assert (
            response.headers.get("access-control-allow-origin")
            != "https://evil.example"
        )


class TestStravaOAuthEndpoints:
    def test_connect_uses_signed_state(self, client, auth_headers, test_user, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "strava_client_id", "12345")
        monkeypatch.setattr(settings, "strava_redirect_uri", "http://localhost/cb")

        response = client.get("/api/strava/connect", headers=auth_headers)
        assert response.status_code == 200

        auth_url = response.json()["auth_url"]
        state = unquote(auth_url.split("state=")[1])
        assert state != str(test_user.id)
        assert verify_oauth_state(state) == test_user.id

    def test_callback_rejects_invalid_state(self, client):
        response = client.get(
            "/api/strava/callback", params={"code": "x", "state": "garbage"}
        )
        assert response.status_code == 400

    def test_callback_rejects_missing_state(self, client):
        response = client.get("/api/strava/callback", params={"code": "x"})
        assert response.status_code == 400
