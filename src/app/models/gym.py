"""
Gym model - climbing gyms/rocódromos.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Enum
from sqlalchemy.orm import relationship
import enum

from app.db.base import Base


class GradingSystemType(str, enum.Enum):
    """Types of grading systems used by gyms."""
    COLORS = "colors"          # Colores sin escala definida
    V_SCALE = "v-scale"        # V0, V1, V2... (Hueco scale)
    FONT_SCALE = "font-scale"  # 6A, 6B, 7A... (Fontainebleau)
    CIRCUIT = "circuit"        # Circuitos numerados
    CUSTOM = "custom"          # Sistema personalizado


class Gym(Base):
    """Climbing gym entity."""
    
    __tablename__ = "gyms"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    
    # Location
    location = Column(String(255), nullable=True)  # Address or description
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Grading system
    grading_system_type = Column(
        Enum(GradingSystemType),
        default=GradingSystemType.COLORS,
        nullable=False
    )
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    home_users = relationship("User", back_populates="home_gym")
    grades = relationship("Grade", back_populates="gym", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="gym", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Gym {self.name}>"
