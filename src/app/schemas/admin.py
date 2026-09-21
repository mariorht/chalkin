"""
Admin schemas - user lookup and password reset link generation.
"""
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class AdminUserResult(BaseModel):
    """A user row shown in the admin user search."""
    id: int
    username: str
    email: str
    is_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PasswordResetLink(BaseModel):
    """Generated password reset link plus a ready-to-send email.

    ``email_body`` contains a ``{link}`` placeholder that the frontend replaces
    with the absolute reset URL (built from the browser origin).
    """
    reset_path: str
    token: str
    expires_at: datetime
    email_subject: str
    email_body: str


class PasswordResetRequest(BaseModel):
    """Payload for the public reset endpoint."""
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)


class PasswordResetResponse(BaseModel):
    """Result of a successful password reset."""
    message: str = "Password updated successfully"
