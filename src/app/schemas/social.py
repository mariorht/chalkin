"""
Social schemas for friends and feed.
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class UserSearchResult(BaseModel):
    """User info for search results."""
    id: int
    username: str
    profile_picture: Optional[str] = None
    friendship_status: Optional[str] = None  # None, pending, accepted, pending_received

    model_config = ConfigDict(from_attributes=True)


class FriendshipCreate(BaseModel):
    """Schema for sending a friend request."""
    friend_id: int


class FriendshipResponse(BaseModel):
    """Schema for friendship response."""
    id: int
    user_id: int
    friend_id: int
    status: str
    created_at: datetime
    
    # Include user info
    user_username: Optional[str] = None
    user_profile_picture: Optional[str] = None
    friend_username: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FriendResponse(BaseModel):
    """Schema for a friend in the friends list."""
    id: int
    username: str
    profile_picture: Optional[str] = None
    friendship_id: int
    since: datetime  # When friendship was accepted

    model_config = ConfigDict(from_attributes=True)


class FeedItem(BaseModel):
    """A single item in the activity feed."""
    session_id: int
    user_id: int
    username: str
    profile_picture: Optional[str] = None
    gym_id: int
    gym_name: str
    gym_location: Optional[str] = None
    title: Optional[str] = None
    subtitle: Optional[str] = None
    date: date
    started_at: datetime
    ended_at: Optional[datetime] = None
    total_ascents: int = 0
    flashes: int = 0
    sends: int = 0
    max_grade_label: Optional[str] = None
    is_own: bool = False  # True if this is the current user's session

    model_config = ConfigDict(from_attributes=True)


class FeedResponse(BaseModel):
    """Response for the activity feed."""
    items: List[FeedItem]
    has_more: bool = False
