"""
Session model - a climbing session or a home training activity.
"""
import enum
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship

from app.db.base import Base


class ActivityType(str, enum.Enum):
    """Type of activity a session represents.

    - GYM: climbing at a gym. Requires a gym and allows ascents (grades are
      gym-scoped).
    - HOME: training at home or anywhere outside a gym. No gym, no grades;
      only complementary exercises (and force measurements).
    """
    GYM = "gym"
    HOME = "home"


class Session(Base):
    """
    Session entity - a visit to a gym or a training activity.

    When ``activity_type`` is ``gym`` the session is tied to a gym and can log
    ascents. When it is ``home`` there is no gym and only exercises/measurements
    apply.
    """
    
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    gym_id = Column(Integer, ForeignKey("gyms.id"), nullable=True)
    activity_type = Column(Enum(ActivityType), default=ActivityType.GYM, nullable=False)
    
    # When
    date = Column(Date, default=date.today, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    
    # Session info
    title = Column(String(100), nullable=True)
    subtitle = Column(String(200), nullable=True)
    
    # Notes about the session
    notes = Column(Text, nullable=True)
    
    # Strava integration
    strava_activity_id = Column(Integer, nullable=True)  # Strava activity ID if uploaded
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    gym = relationship("Gym", back_populates="sessions")
    ascents = relationship("Ascent", back_populates="session", cascade="all, delete-orphan")
    exercises = relationship("SessionExercise", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Session {self.id} - {self.date}>"
