"""
SenseRep schemas - force reps recorded with Chalkin Sense.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class SenseRepBase(BaseModel):
    """Metrics of a single measured rep."""
    set_index: int = Field(1, ge=1)
    rep_index: int = Field(1, ge=0)
    peak_force_kg: Optional[float] = Field(None, ge=0)
    mean_force_kg: Optional[float] = Field(None, ge=0)
    rfd_kg_s: Optional[float] = None
    tut_s: Optional[float] = Field(None, ge=0)
    duration_s: Optional[float] = Field(None, ge=0)
    source: str = "sense"  # sense | manual
    calibration_zero: Optional[float] = None
    calibration_scale: Optional[float] = None
    measured_at: Optional[datetime] = None


class SenseRepCreate(SenseRepBase):
    """Schema for creating a rep."""
    pass


class SenseRepResponse(SenseRepBase):
    """Schema for rep responses."""
    id: int
    exercise_id: int
    session_id: int
    measured_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
