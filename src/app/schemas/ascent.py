"""
Ascent schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class AscentStatus(str, Enum):
    """Status of an ascent attempt."""
    FLASH = "flash"
    SEND = "send"
    REPEAT = "repeat"
    PROJECT = "project"
    ATTEMPT = "attempt"


class AscentBase(BaseModel):
    """Base ascent schema with common fields."""
    grade_id: int
    status: AscentStatus = AscentStatus.SEND
    attempts: int = Field(default=1, ge=1)
    notes: Optional[str] = None
    photo_url: Optional[str] = Field(None, max_length=500)


class AscentCreate(AscentBase):
    """Schema for creating a new ascent."""
    pass


class AscentUpdate(BaseModel):
    """Schema for updating ascent info."""
    grade_id: Optional[int] = None
    status: Optional[AscentStatus] = None
    attempts: Optional[int] = Field(None, ge=1)
    notes: Optional[str] = None
    photo_url: Optional[str] = Field(None, max_length=500)


class AscentResponse(AscentBase):
    """Schema for ascent responses."""
    id: int
    session_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AscentWithGrade(AscentResponse):
    """Schema for ascent with grade details."""
    grade_label: str
    grade_color_hex: Optional[str] = None
    relative_difficulty: float

    class Config:
        from_attributes = True
