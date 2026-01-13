"""
SessionExercise model - complementary training exercises in a session.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class SessionExercise(Base):
    """
    SessionExercise entity - complementary exercises like pullups, campus, etc.
    
    Allows users to track training exercises beyond boulder problems.
    """
    
    __tablename__ = "session_exercises"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Exercise details
    exercise_type = Column(String(50), nullable=False)  # pullups, campus, fingerboard, etc.
    sets = Column(Integer, nullable=True)
    reps = Column(String(50), nullable=True)  # Can be "10", "max", "5-3-2", etc.
    weight = Column(Float, nullable=True)  # For weighted exercises
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="exercises")
