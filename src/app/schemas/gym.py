"""
Gym schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class GradingSystemType(str, Enum):
    """Types of grading systems used by gyms."""
    COLORS = "colors"
    V_SCALE = "v-scale"
    FONT_SCALE = "font-scale"
    CIRCUIT = "circuit"
    CUSTOM = "custom"


class GymBase(BaseModel):
    """Base gym schema with common fields."""
    name: str = Field(..., min_length=1, max_length=100)
    location: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    grading_system_type: GradingSystemType = GradingSystemType.COLORS


class GymCreate(GymBase):
    """Schema for creating a new gym."""
    pass


class GymUpdate(BaseModel):
    """Schema for updating gym info."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    location: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    grading_system_type: Optional[GradingSystemType] = None


class GymResponse(GymBase):
    """Schema for gym responses."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GymWithGrades(GymResponse):
    """Schema for gym with its grades included."""
    grades: List["GradeResponse"] = []

    class Config:
        from_attributes = True


# Forward reference resolution
from app.schemas.grade import GradeResponse
GymWithGrades.model_rebuild()
