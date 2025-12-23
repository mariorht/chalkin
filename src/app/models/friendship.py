"""
Friendship model for social features.
"""
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class FriendshipStatus(str, PyEnum):
    """Status of a friendship request."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class Friendship(Base):
    """
    Friendship model - represents a friend relationship between two users.
    user_id sends the request, friend_id receives it.
    """
    __tablename__ = "friendships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    friend_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(FriendshipStatus), default=FriendshipStatus.PENDING, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="sent_friend_requests")
    friend = relationship("User", foreign_keys=[friend_id], backref="received_friend_requests")

    __table_args__ = (
        UniqueConstraint('user_id', 'friend_id', name='unique_friendship'),
    )

    def __repr__(self):
        return f"<Friendship {self.user_id} -> {self.friend_id} ({self.status})>"
