"""
SessionExercise schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class SessionExerciseBase(BaseModel):
    """Base session exercise schema with common fields."""
    exercise_type: str = Field(..., max_length=50, description="Type of exercise (pullups, campus, etc.)")
    sets: Optional[int] = Field(None, ge=1, description="Number of sets")
    reps: Optional[str] = Field(None, max_length=50, description="Reps (e.g., '10', 'max', '5-3-2')")
    weight: Optional[float] = Field(None, description="Weight in kg for weighted exercises")
    notes: Optional[str] = None
    # Fingerboard/hangboard context
    protocol: Optional[str] = Field(None, max_length=50)
    edge_depth_mm: Optional[int] = Field(None, ge=0)
    hand: Optional[str] = Field(None, max_length=10)  # left | right | both
    grip: Optional[str] = Field(None, max_length=30)  # open | half_crimp | full_crimp | pinch | mono | two_finger | other
    added_weight_kg: Optional[float] = None
    body_weight_kg: Optional[float] = Field(None, gt=0)


class SessionExerciseCreate(SessionExerciseBase):
    """Schema for creating a new exercise."""
    pass


class SessionExerciseUpdate(BaseModel):
    """Schema for updating exercise info."""
    exercise_type: Optional[str] = Field(None, max_length=50)
    sets: Optional[int] = Field(None, ge=1)
    reps: Optional[str] = Field(None, max_length=50)
    weight: Optional[float] = None
    notes: Optional[str] = None
    protocol: Optional[str] = Field(None, max_length=50)
    edge_depth_mm: Optional[int] = Field(None, ge=0)
    hand: Optional[str] = Field(None, max_length=10)
    grip: Optional[str] = Field(None, max_length=30)
    added_weight_kg: Optional[float] = None
    body_weight_kg: Optional[float] = Field(None, gt=0)


class SessionExerciseResponse(SessionExerciseBase):
    """Schema for exercise responses."""
    id: int
    session_id: int
    created_at: datetime
    sense_reps: List["SenseRepResponse"] = []

    model_config = ConfigDict(from_attributes=True)


# Forward reference resolution
from app.schemas.sense_rep import SenseRepResponse
SessionExerciseResponse.model_rebuild()

