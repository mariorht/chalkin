"""
Security utilities for password hashing and JWT tokens.
"""
import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _token_cipher():
    """Return a Fernet instance for encrypting third-party tokens at rest.

    Uses TOKEN_ENCRYPTION_KEY when provided, otherwise derives a stable key
    from SECRET_KEY so no extra configuration is required.
    """
    from cryptography.fernet import Fernet

    if settings.token_encryption_key:
        return Fernet(settings.token_encryption_key.encode("utf-8"))
    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_token(plaintext: str) -> str:
    """Encrypt a token before storing it in the database."""
    return _token_cipher().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_token(value: str) -> str:
    """Decrypt a stored token. Returns the value unchanged if it is not
    encrypted (legacy plaintext rows written before encryption existed)."""
    from cryptography.fernet import InvalidToken

    try:
        return _token_cipher().decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return value


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed one."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def hash_token(token: str) -> str:
    """Hash a reset/invitation token for safe storage (SHA-256 hex digest)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    now = datetime.now(timezone.utc)
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    
    # iat is a float epoch so tokens issued before a password change can be revoked
    to_encode.update({"exp": expire, "iat": time.time()})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_oauth_state(user_id: int, ttl_seconds: int = 1800) -> str:
    """Create a signed, expiring ``state`` value for OAuth flows.

    Prevents CSRF/account-linking attacks: the value is unpredictable and
    tamper-proof, unlike a bare user id.
    """
    payload = json.dumps(
        {"sub": str(user_id), "exp": int(time.time()) + ttl_seconds},
        separators=(",", ":"),
    ).encode("utf-8")
    body = _b64url_encode(payload)
    signature = hmac.new(
        settings.secret_key.encode("utf-8"), body.encode("ascii"), hashlib.sha256
    ).digest()
    return f"{body}.{_b64url_encode(signature)}"


def verify_oauth_state(state: str) -> Optional[int]:
    """Verify a signed OAuth ``state`` and return the user id, or None."""
    try:
        body, signature = state.split(".", 1)
        expected = hmac.new(
            settings.secret_key.encode("utf-8"), body.encode("ascii"), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(expected, _b64url_decode(signature)):
            return None
        payload = json.loads(_b64url_decode(body))
        if int(payload.get("exp", 0)) < time.time():
            return None
        return int(payload["sub"])
    except Exception:
        return None
