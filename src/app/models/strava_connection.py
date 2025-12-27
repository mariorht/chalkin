"""
Strava connection model - OAuth tokens for Strava integration.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship

from app.db.base import Base


class StravaConnection(Base):
    """Strava OAuth connection for a user."""
    
    __tablename__ = "strava_connections"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Strava athlete ID
    athlete_id = Column(BigInteger, nullable=False, index=True)
    
    # OAuth tokens
    access_token = Column(String(255), nullable=False)
    refresh_token = Column(String(255), nullable=False)
    expires_at = Column(BigInteger, nullable=False)  # Unix timestamp
    
    # Token scope (e.g., "read,activity:write")
    scope = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("User", backref="strava_connection")
    
    def __repr__(self):
        return f"<StravaConnection user_id={self.user_id} athlete_id={self.athlete_id}>"
