"""
Session schemas for request/response validation.
"""
from datetime import datetime, date as date_type
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class SessionBase(BaseModel):
    """Base session schema with common fields."""
    gym_id: int
    date: date_type = Field(default_factory=date_type.today)
    title: Optional[str] = None
    subtitle: Optional[str] = None
    notes: Optional[str] = None


class SessionCreate(SessionBase):
    """Schema for creating a new session."""
    pass


class SessionUpdate(BaseModel):
    """Schema for updating session info."""
    gym_id: Optional[int] = None
    date: Optional[date_type] = None
    title: Optional[str] = None
    subtitle: Optional[str] = None
    notes: Optional[str] = None
    ended_at: Optional[datetime] = None


class SessionResponse(SessionBase):
    """Schema for session responses."""
    id: int
    user_id: int
    title: Optional[str] = None
    subtitle: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Extended fields for UI
    gym_name: Optional[str] = None
    total_ascents: int = 0
    flashes: int = 0
    sends: int = 0
    max_grade_label: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SessionWithAscents(SessionResponse):
    """Schema for session with all ascents included."""
    ascents: List["AscentResponse"] = []
    
    # Computed summary fields
    total_ascents: int = 0
    sends: int = 0
    flashes: int = 0
    projects: int = 0
    
    # Owner info (for viewing friend's sessions)
    owner_username: Optional[str] = None
    is_own: bool = True

    model_config = ConfigDict(from_attributes=True)


class SessionSummary(BaseModel):
    """Quick summary of a session."""
    id: int
    date: date_type
    gym_name: str
    total_ascents: int
    max_grade_label: Optional[str] = None


# Forward reference resolution
from app.schemas.ascent import AscentResponse
SessionWithAscents.model_rebuild()
