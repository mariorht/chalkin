"""
Ascent model - individual boulder problems climbed.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
import enum

from app.db.base import Base


class AscentStatus(str, enum.Enum):
    """Status of an ascent attempt."""
    FLASH = "flash"           # First try, no beta
    SEND = "send"             # Completed (encadenado)
    REPEAT = "repeat"         # Done it before, did it again
    PROJECT = "project"       # Attempted but not completed
    ATTEMPT = "attempt"       # Just tried, for logging volume


class Ascent(Base):
    """
    Ascent entity - a single boulder problem climbed.
    
    This is the core tracking unit - each time you climb a boulder,
    you log an ascent.
    """
    
    __tablename__ = "ascents"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    grade_id = Column(Integer, ForeignKey("grades.id"), nullable=False)
    
    # Ascent details
    status = Column(Enum(AscentStatus), default=AscentStatus.SEND, nullable=False)
    
    # Optional: number of attempts before sending
    attempts = Column(Integer, default=1)
    
    # Optional: photo of the boulder
    photo_url = Column(String(500), nullable=True)
    
    # Optional: notes about the climb
    notes = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="ascents")
    grade = relationship("Grade", back_populates="ascents")
    
    def __repr__(self):
        return f"<Ascent {self.id} - {self.status.value}>"
