"""
Competition schemas for request/response validation.
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class CompetitionStatus(str, Enum):
    """Lifecycle of a competition."""
    DRAFT = "draft"
    ACTIVE = "active"
    FINISHED = "finished"


class CompetitionPointItem(BaseModel):
    """Points for a single grade within a competition."""
    grade_id: int
    points: int = Field(..., ge=0, le=10000)


class CompetitionPointResponse(CompetitionPointItem):
    """Points for a grade, with display info."""
    id: int
    label: Optional[str] = None
    color_hex: Optional[str] = None
    relative_difficulty: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class CompetitionBase(BaseModel):
    """Base competition schema with common fields."""
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=500)
    start_date: date
    end_date: date


class CompetitionCreate(CompetitionBase):
    """Schema for creating a competition (admin)."""
    gym_id: int
    status: CompetitionStatus = CompetitionStatus.DRAFT
    # Rest weeks (1-based week numbers) where the event is paused
    week_offsets: List[int] = []
    points: List[CompetitionPointItem] = []


class CompetitionUpdate(BaseModel):
    """Schema for updating a competition (admin)."""
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=500)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[CompetitionStatus] = None
    week_offsets: Optional[List[int]] = None


class CompetitionResponse(CompetitionBase):
    """Competition with its gym and points."""
    id: int
    gym_id: int
    gym_name: Optional[str] = None
    status: CompetitionStatus
    is_running: bool = False
    total_weeks: int = 0
    week_offsets: List[int] = []
    points: List[CompetitionPointResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompetitionWeekResponse(BaseModel):
    """A single week of a competition, with its bounds."""
    week: int
    start_date: date
    end_date: date
    is_current: bool = False
    is_rest: bool = False


class GradeBreakdown(BaseModel):
    """How many boulders of a grade a participant has scored."""
    grade_id: int
    label: Optional[str] = None
    color_hex: Optional[str] = None
    count: int = 0
    points: int = 0
    # League block numbers scored for this grade (sorted, de-duplicated)
    blocks: List[int] = []


class LeaderboardEntry(BaseModel):
    """One participant's standing in the leaderboard."""
    user_id: int
    username: str
    profile_picture: Optional[str] = None
    points: int = 0
    # Deduplicated count of scoring boulders (repeat attempts count once)
    scored_boulders: int = 0
    is_me: bool = False
    # Per-grade breakdown (only filled for the total standings)
    breakdown: List[GradeBreakdown] = []


class CompetitionLeaderboard(BaseModel):
    """Leaderboard for a competition, with weekly breakdown."""
    competition_id: int
    competition_name: str
    gym_name: Optional[str] = None
    status: CompetitionStatus
    weeks: List[CompetitionWeekResponse] = []
    # entries[week-1] is the ranking for that week (empty list if no data)
    weekly: List[List[LeaderboardEntry]] = []
    total: List[LeaderboardEntry] = []
