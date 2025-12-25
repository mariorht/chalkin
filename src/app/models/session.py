"""
Session model - a climbing session at a gym.
"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class Session(Base):
    """
    Climbing session entity.
    
    Represents a single visit to a gym where the user logs their climbs.
    """
    
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    gym_id = Column(Integer, ForeignKey("gyms.id"), nullable=False)
    
    # When
    date = Column(Date, default=date.today, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    
    # Session info
    title = Column(String(100), nullable=True)
    subtitle = Column(String(200), nullable=True)
    
    # Notes about the session
    notes = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    gym = relationship("Gym", back_populates="sessions")
    ascents = relationship("Ascent", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Session {self.id} - {self.date}>"
