"""
Competition model - league events (e.g. the Boulder Up Superliga).

A competition is tied to one gym and runs over a date range. Points are
awarded per grade (the gym's grades, e.g. its colours), defined once for the
whole event. Weeks are derived from the calendar, so there is no week table.

Participation is implicit: a user takes part as soon as they tag a boulder as
belonging to the competition.
"""
import enum
from datetime import datetime, date, timedelta
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Date,
    ForeignKey,
    Enum,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class CompetitionStatus(str, enum.Enum):
    """Lifecycle of a competition."""
    DRAFT = "draft"        # Configured but not visible to users
    ACTIVE = "active"      # Running: boulders can be tagged
    FINISHED = "finished"  # Over: kept for the record


class Competition(Base):
    """A league event held at a gym over a date range."""

    __tablename__ = "competitions"

    id = Column(Integer, primary_key=True, index=True)
    gym_id = Column(Integer, ForeignKey("gyms.id"), nullable=False, index=True)

    name = Column(String(120), nullable=False)
    description = Column(String(500), nullable=True)

    # Event window (inclusive)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    status = Column(
        Enum(CompetitionStatus), default=CompetitionStatus.DRAFT, nullable=False
    )

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    gym = relationship("Gym", back_populates="competitions")
    points = relationship(
        "CompetitionPoint",
        back_populates="competition",
        cascade="all, delete-orphan",
    )

    @property
    def is_running(self) -> bool:
        """True if today falls inside the event window (and it is active)."""
        if self.status != CompetitionStatus.ACTIVE:
            return False
        today = date.today()
        return self.start_date <= today <= self.end_date

    def contains(self, day: date) -> bool:
        """True if ``day`` falls inside the event window."""
        return self.start_date <= day <= self.end_date

    def week_index(self, day: date) -> int:
        """1-based week number of ``day`` within the event.

        Week 1 always starts on ``start_date``; each following week starts 7
        days later. Returns 0 if the day is outside the event.
        """
        if not self.contains(day):
            return 0
        return (day - self.start_date).days // 7 + 1

    def week_bounds(self, week: int) -> tuple[date, date]:
        """Inclusive (start, end) dates of a 1-based week number."""
        start = self.start_date + timedelta(days=(week - 1) * 7)
        end = min(start + timedelta(days=6), self.end_date)
        return start, end

    @property
    def total_weeks(self) -> int:
        """Number of weeks the event spans."""
        return self.week_index(self.end_date)

    def __repr__(self) -> str:
        return f"<Competition {self.id} - {self.name} @ {self.gym_id}>"


class CompetitionPoint(Base):
    """Points awarded for completing a boulder of a given grade in the event."""

    __tablename__ = "competition_points"

    id = Column(Integer, primary_key=True, index=True)
    competition_id = Column(
        Integer,
        ForeignKey("competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Grade is gym-scoped, so it also guarantees it belongs to the event's gym.
    grade_id = Column(
        Integer,
        ForeignKey("grades.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    points = Column(Integer, nullable=False, default=0)

    # Relationships
    competition = relationship("Competition", back_populates="points")
    grade = relationship("Grade")

    __table_args__ = (
        UniqueConstraint(
            "competition_id", "grade_id", name="unique_competition_grade_points"
        ),
    )

    def __repr__(self) -> str:
        return f"<CompetitionPoint comp={self.competition_id} grade={self.grade_id} = {self.points}>"
