"""
Grade schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import re


class GradeBase(BaseModel):
    """Base grade schema with common fields."""
    label: str = Field(..., min_length=1, max_length=50)
    color_hex: Optional[str] = Field(None, max_length=7)
    relative_difficulty: float = Field(..., ge=0, le=15)
    order: int = Field(default=0)

    @field_validator('color_hex')
    @classmethod
    def validate_color_hex(cls, v: Optional[str]) -> Optional[str]:
        """Validate hex color format."""
        if v is None:
            return v
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError('color_hex must be in format #RRGGBB')
        return v.upper()


class GradeCreate(GradeBase):
    """Schema for creating a new grade."""
    gym_id: int


class GradeBulkItem(BaseModel):
    """Schema for a single grade in bulk creation (without gym_id)."""
    label: str = Field(..., min_length=1, max_length=50)
    color_hex: Optional[str] = Field(None, max_length=7)
    relative_difficulty: float = Field(..., ge=0, le=15)
    order: int = Field(default=0)

    @field_validator('color_hex')
    @classmethod
    def validate_color_hex(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError('color_hex must be in format #RRGGBB')
        return v.upper()


class BulkGradeCreate(BaseModel):
    """Schema for bulk grade creation."""
    gym_id: int
    grades: List[GradeBulkItem]


class GradeUpdate(BaseModel):
    """Schema for updating grade info."""
    label: Optional[str] = Field(None, min_length=1, max_length=50)
    color_hex: Optional[str] = Field(None, max_length=7)
    relative_difficulty: Optional[float] = Field(None, ge=0, le=15)
    order: Optional[int] = None

    @field_validator('color_hex')
    @classmethod
    def validate_color_hex(cls, v: Optional[str]) -> Optional[str]:
        """Validate hex color format."""
        if v is None:
            return v
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError('color_hex must be in format #RRGGBB')
        return v.upper()


class GradeResponse(GradeBase):
    """Schema for grade responses."""
    id: int
    gym_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
