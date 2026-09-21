"""
Application configuration using Pydantic Settings.
Loads from environment variables or .env file.
"""
from functools import lru_cache
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

# Known placeholder keys that must never be used outside development.
INSECURE_SECRET_KEYS = {
    "",
    "your-secret-key-change-in-production",
    "dev-secret-key-change-in-production",
}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App info
    app_name: str = "Chalkin"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # Database
    database_url: str = "sqlite:///./data/chalkin.db"
    
    # Data directory for uploads and persistent files
    # In Docker: /app/data, Local: ./data (relative to src/)
    data_dir: str = "./data"
    
    # JWT Auth
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 1 week

    # Optional Fernet key used to encrypt third-party tokens at rest.
    # If unset, a key is derived from SECRET_KEY.
    token_encryption_key: Optional[str] = None
    
    # File uploads
    upload_dir: str = "uploads"
    max_file_size: int = 5 * 1024 * 1024  # 5MB

    # CORS: comma-separated list of allowed origins. Same-origin requests
    # (the normal case) do not need to be listed.
    cors_origins: str = "http://localhost:8001,http://localhost:8000"

    # Web Push (VAPID)
    vapid_public_key: Optional[str] = None
    vapid_private_key: Optional[str] = None
    vapid_subject: Optional[str] = "mailto:support@example.com"
    
    # Strava OAuth
    strava_client_id: Optional[str] = None
    strava_client_secret: Optional[str] = None
    strava_redirect_uri: Optional[str] = None  # e.g., https://yourdomain.com/api/strava/callback
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @model_validator(mode="after")
    def _require_strong_secret_key(self):
        """Refuse to start with a placeholder SECRET_KEY outside debug mode."""
        if not self.debug and self.secret_key in INSECURE_SECRET_KEYS:
            raise ValueError(
                "SECRET_KEY must be set to a strong, unique value when DEBUG is "
                "false. Generate one with: openssl rand -hex 32 "
                "(or set DEBUG=true for local development)."
            )
        return self


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


settings = get_settings()
