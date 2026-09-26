"""
SenseRep model - a single rep (pull) measured with Chalkin Sense.

Each rep belongs to a SessionExercise (e.g. a fingerboard/campus set). Metrics
mirror the SDK's ``pullEnd`` event. Raw force curves are intentionally NOT
stored for training reps (``curve`` is reserved/unused for now).
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class SenseRep(Base):
    """A single force rep recorded with Chalkin Sense."""

    __tablename__ = "sense_reps"

    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(
        Integer,
        ForeignKey("session_exercises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Denormalised for easy session-level queries.
    session_id = Column(
        Integer,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Where this rep sits within the exercise.
    set_index = Column(Integer, default=1)
    rep_index = Column(Integer, default=1)

    # Metrics (same rules as the SDK/firmware).
    peak_force_kg = Column(Float, nullable=True)
    mean_force_kg = Column(Float, nullable=True)
    rfd_kg_s = Column(Float, nullable=True)
    tut_s = Column(Float, nullable=True)
    duration_s = Column(Float, nullable=True)

    # Sensor metadata / traceability.
    source = Column(String(20), default="sense")  # sense | manual
    calibration_zero = Column(Float, nullable=True)
    calibration_scale = Column(Float, nullable=True)

    # Reserved for future raw/downsampled force curves (not populated for now).
    curve = Column(Text, nullable=True)

    measured_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    exercise = relationship("SessionExercise", back_populates="sense_reps")

    def __repr__(self):
        return f"<SenseRep {self.id} exercise={self.exercise_id} peak={self.peak_force_kg}>"
