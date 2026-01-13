"""
SessionExercise schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class SessionExerciseBase(BaseModel):
    """Base session exercise schema with common fields."""
    exercise_type: str = Field(..., max_length=50, description="Type of exercise (pullups, campus, etc.)")
    sets: Optional[int] = Field(None, ge=1, description="Number of sets")
    reps: Optional[str] = Field(None, max_length=50, description="Reps (e.g., '10', 'max', '5-3-2')")
    weight: Optional[float] = Field(None, description="Weight in kg for weighted exercises")
    notes: Optional[str] = None


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


class SessionExerciseResponse(SessionExerciseBase):
    """Schema for exercise responses."""
    id: int
    session_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
