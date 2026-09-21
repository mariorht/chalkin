"""
Invitation schemas - for invitation-only registration.
"""
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional


class InvitationCreate(BaseModel):
    """Schema for creating a new invitation (no fields needed from user)."""
    pass


class InvitationResponse(BaseModel):
    """Schema for invitation response.

    The raw token is intentionally not exposed: only its hash is stored, and the
    shareable link is returned once at creation time (``InvitationLink``).
    """
    id: int
    created_by_user_id: int
    created_at: datetime
    expires_at: datetime
    used: bool
    used_by_user_id: Optional[int] = None
    used_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class InvitationLink(BaseModel):
    """Schema for returning an invitation link to the user."""
    token: str
    expires_at: datetime
    link: str
