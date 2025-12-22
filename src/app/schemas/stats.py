"""
Statistics schemas for user progress and analytics.
"""
from datetime import date
from typing import List, Optional
from pydantic import BaseModel


class GradeDistribution(BaseModel):
    """Distribution of ascents by grade."""
    grade_label: str
    color_hex: Optional[str] = None
    relative_difficulty: float
    count: int
    sends: int
    flashes: int


class WeeklyStats(BaseModel):
    """Stats for a single week."""
    week_start: date
    week_end: date
    total_sessions: int
    total_ascents: int
    total_sends: int
    total_flashes: int
    max_grade_sent: Optional[str] = None
    max_relative_difficulty: Optional[float] = None


class GymStats(BaseModel):
    """Stats for a specific gym."""
    gym_id: int
    gym_name: str
    total_sessions: int
    total_ascents: int
    favorite_grade: Optional[str] = None


class UserStats(BaseModel):
    """Complete user statistics."""
    # Overall totals
    total_sessions: int
    total_ascents: int
    total_sends: int
    total_flashes: int
    
    # Progress indicators
    max_grade_ever: Optional[str] = None
    max_relative_difficulty: Optional[float] = None
    current_max_grade: Optional[str] = None  # Last 30 days
    
    # Recent activity
    sessions_this_week: int
    sessions_this_month: int
    ascents_this_week: int
    ascents_this_month: int
    sends_this_week: int = 0
    flashes_this_week: int = 0
    max_grade_label: Optional[str] = None  # Alias for max_grade_ever for frontend
    
    # Streaks
    current_streak_days: int = 0
    longest_streak_days: int = 0
    
    # Detailed breakdowns
    grade_distribution: List[GradeDistribution] = []
    weekly_progress: List[WeeklyStats] = []
    gym_breakdown: List[GymStats] = []


class LeaderboardEntry(BaseModel):
    """Entry in a leaderboard."""
    rank: int
    user_id: int
    username: str
    value: float  # Whatever metric we're ranking by
    

class SessionFeedItem(BaseModel):
    """A single item in the activity feed."""
    session_id: int
    user_id: int
    username: str
    gym_name: str
    date: date
    total_ascents: int
    max_grade: Optional[str] = None
    highlight: Optional[str] = None  # e.g., "New PR!" or "5 Flashes!"
