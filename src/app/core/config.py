"""
Application configuration using Pydantic Settings.
Loads from environment variables or .env file.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


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
    
    # File uploads
    upload_dir: str = "uploads"
    max_file_size: int = 5 * 1024 * 1024  # 5MB

    # Web Push (VAPID)
    vapid_public_key: Optional[str] = None
    vapid_private_key: Optional[str] = None
    vapid_subject: Optional[str] = "mailto:support@example.com"
    
    # Strava OAuth
    strava_client_id: Optional[str] = None
    strava_client_secret: Optional[str] = None
    strava_redirect_uri: Optional[str] = None  # e.g., https://yourdomain.com/api/strava/callback
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


settings = get_settings()
