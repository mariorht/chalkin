"""
Grade model - difficulty levels within a gym.
This is the KEY model for solving the "each gym grades differently" problem.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship

from app.db.base import Base


class Grade(Base):
    """
    Grade/Difficulty level entity.
    
    Each gym has its own set of grades. The 'relative_difficulty' field
    allows comparing grades across different gyms.
    
    Example:
    - Gym A (colors): "Rojo" -> relative_difficulty = 5
    - Gym B (v-scale): "V4" -> relative_difficulty = 5
    These would be considered equivalent difficulty.
    """
    
    __tablename__ = "grades"
    
    id = Column(Integer, primary_key=True, index=True)
    gym_id = Column(Integer, ForeignKey("gyms.id"), nullable=False)
    
    # Display info
    label = Column(String(50), nullable=False)  # "V4", "Rojo", "6A+"
    color_hex = Column(String(7), nullable=True)  # "#FF0000" for visual display
    
    # Difficulty comparison - allows comparing across gyms
    # Scale: 1-15 (roughly maps to V0-V15 / 4-8C+)
    relative_difficulty = Column(Float, nullable=False)
    
    # Order within the gym's scale (for sorting)
    order = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    gym = relationship("Gym", back_populates="grades")
    ascents = relationship("Ascent", back_populates="grade", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Grade {self.label} @ {self.gym_id}>"
