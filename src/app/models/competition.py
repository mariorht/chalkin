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

    # Rest weeks: week numbers (1-based) where the event is paused. During a
    # rest week boulders can neither be tagged nor score.
    # Stored as a comma-separated list of ints (e.g. "5,6"); empty/NULL = none.
    week_offsets = Column(String(255), nullable=True, default="")

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
        """True if today falls inside the event window (and it is active).

        A rest week does not stop the event from running, but nothing scores.
        """
        if self.status != CompetitionStatus.ACTIVE:
            return False
        today = date.today()
        return self.start_date <= today <= self.end_date

    def contains(self, day: date) -> bool:
        """True if ``day`` falls inside the event window."""
        return self.start_date <= day <= self.end_date

    @property
    def offset_weeks(self) -> set[int]:
        """Week numbers that are rest weeks."""
        if not self.week_offsets:
            return set()
        result = set()
        for chunk in str(self.week_offsets).split(","):
            chunk = chunk.strip()
            if chunk.isdigit():
                result.add(int(chunk))
        return result

    def set_offset_weeks(self, weeks) -> None:
        """Store rest weeks as a normalised, sorted comma-separated string."""
        cleaned = sorted({int(w) for w in weeks if int(w) > 0})
        self.week_offsets = ",".join(str(w) for w in cleaned)

    def is_rest_week(self, week: int) -> bool:
        """True if a 1-based week number is a rest week."""
        return week in self.offset_weeks

    def is_active_week(self, week: int) -> bool:
        """True if a week scores (inside the event and not a rest week)."""
        return 1 <= week <= self.total_weeks and not self.is_rest_week(week)

    def week_index(self, day: date) -> int:
        """1-based week number of ``day`` within the event.

        Weeks are natural weeks: Monday to Sunday. Week 1 starts on
        ``start_date`` and ends on the first Sunday; from then on, each week
        runs Monday to Sunday. Returns 0 if the day is outside the event.
        """
        if not self.contains(day):
            return 0
        first_monday = self.start_date - timedelta(days=self.start_date.weekday())
        return (day - first_monday).days // 7 + 1

    def week_bounds(self, week: int) -> tuple[date, date]:
        """Inclusive (start, end) dates of a 1-based week number.

        Follows the Monday-to-Sunday rule (see ``week_index``). Week 1 starts
        on ``start_date``; the last week may end on ``end_date``.
        """
        first_monday = self.start_date - timedelta(days=self.start_date.weekday())
        start = first_monday + timedelta(days=(week - 1) * 7)
        end = min(start + timedelta(days=6), self.end_date)
        # Week 1 never starts before the event does
        start = max(start, self.start_date)
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
