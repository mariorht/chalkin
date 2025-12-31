"""
Invitation model - for invitation-only registration.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.db.base import Base


class Invitation(Base):
    """Invitation entity for user registration."""
    
    __tablename__ = "invitations"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(255), unique=True, index=True, nullable=False)  # Unique invitation token
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who created the invitation
    
    # Invitation validity
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)  # Token expiry date (24 hours from creation)
    
    # Usage tracking
    used = Column(Boolean, default=False)  # Whether the invitation has been used
    used_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # User who used this invitation
    used_at = Column(DateTime, nullable=True)  # When the invitation was used
    
    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    used_by = relationship("User", foreign_keys=[used_by_user_id])
    
    def __repr__(self):
        return f"<Invitation {self.token[:8]}... by user {self.created_by_user_id}>"
