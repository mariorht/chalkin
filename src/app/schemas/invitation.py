"""
Invitation schemas - for invitation-only registration.
"""
from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class InvitationCreate(BaseModel):
    """Schema for creating a new invitation (no fields needed from user)."""
    pass


class InvitationResponse(BaseModel):
    """Schema for invitation response."""
    id: int
    token: str
    created_by_user_id: int
    created_at: datetime
    expires_at: datetime
    used: bool
    used_by_user_id: Optional[int] = None
    used_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class InvitationLink(BaseModel):
    """Schema for returning an invitation link to the user."""
    token: str
    expires_at: datetime
    link: str
