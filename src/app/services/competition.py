"""
Competition scoring.

Points are awarded per grade for the whole event. An ascent scores only once
per boulder (a repeat of the same grade in the same competition-day counts
once), which keeps "do the same easy block ten times" from farming points.

The functions here are pure-ish: they take a DB session and return plain data,
so they are easy to test.
"""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.ascent import Ascent, AscentStatus
from app.models.competition import Competition, CompetitionPoint, CompetitionStatus
from app.models.friendship import Friendship, FriendshipStatus
from app.models.grade import Grade
from app.models.session import Session as ClimbingSession
from app.models.user import User

# Ascent statuses that do NOT score (you did not complete the boulder)
NON_SCORING_STATUSES = {AscentStatus.PROJECT, AscentStatus.ATTEMPT}


def competition_points_map(db: Session, competition_id: int) -> dict[int, int]:
    """Return {grade_id: points} for a competition."""
    rows = (
        db.query(CompetitionPoint)
        .filter(CompetitionPoint.competition_id == competition_id)
        .all()
    )
    return {row.grade_id: row.points for row in rows}


def scoring_ascents_query(db: Session, competition_id: int):
    """Query for ascents that score in a competition.

    A scoring ascent:
    - belongs to a session in the competition's gym,
    - falls inside the event window,
    - completed the boulder (not a project/attempt),
    - is tagged with the competition,
    - has a grade that awards points.
    """
    competition = db.query(Competition).filter(Competition.id == competition_id).first()
    if competition is None:
        return None

    return (
        db.query(Ascent, ClimbingSession, Grade)
        .join(ClimbingSession, Ascent.session_id == ClimbingSession.id)
        .join(Grade, Ascent.grade_id == Grade.id)
        .join(CompetitionPoint, CompetitionPoint.grade_id == Grade.id)
        .filter(
            CompetitionPoint.competition_id == competition_id,
            Ascent.competition_id == competition_id,
            Ascent.status.notin_(list(NON_SCORING_STATUSES)),
            ClimbingSession.gym_id == competition.gym_id,
            ClimbingSession.date >= competition.start_date,
            ClimbingSession.date <= competition.end_date,
        )
    )


def _dedup_key(user_id: int, grade_id: int, day: date):
    """A boulder is identified by (user, grade, day) within the event.

    The app has no per-boulder catalogue, so the same grade on the same day is
    treated as the same physical block: repeating it does not score twice.
    """
    return (user_id, grade_id, day)


def _accumulate(rows, points_by_grade: dict[int, int], competition: Competition):
    """
    Collapse raw scoring ascents into per-user totals.

    Returns {user_id: {"points": int, "scored": set(keys)}}.
    """
    totals: dict[int, dict] = {}
    for ascent, session, grade in rows:
        points = points_by_grade.get(grade.id, 0)
        user_id = session.user_id
        bucket = totals.setdefault(user_id, {"points": 0, "scored": set()})
        key = _dedup_key(user_id, grade.id, session.date)
        if key in bucket["scored"]:
            continue
        bucket["scored"].add(key)
        bucket["points"] += points
    return totals


def standings(db: Session, competition: Competition) -> dict:
    """
    Build the full standings for a competition.

    Returns a dict with:
    - ``overall``: {user_id: {"points", "boulders"}}
    - ``weekly``: {week_number: {user_id: {"points", "boulders"}}}
    """
    points_by_grade = competition_points_map(db, competition.id)
    query = scoring_ascents_query(db, competition.id)
    rows = query.all() if query is not None else []

    overall: dict[int, dict] = {}
    weekly: dict[int, dict[int, dict]] = {}

    for ascent, session, grade in rows:
        points = points_by_grade.get(grade.id, 0)
        user_id = session.user_id
        week = competition.week_index(session.date)
        # Rest weeks score nothing
        if week < 1 or competition.is_rest_week(week):
            continue
        key = _dedup_key(user_id, grade.id, session.date)

        bucket = overall.setdefault(user_id, {"points": 0, "scored": set()})
        if key not in bucket["scored"]:
            bucket["scored"].add(key)
            bucket["points"] += points

        week_bucket = weekly.setdefault(week, {})
        wb = week_bucket.setdefault(user_id, {"points": 0, "scored": set()})
        if key not in wb["scored"]:
            wb["scored"].add(key)
            wb["points"] += points

    return {"overall": overall, "weekly": weekly}


def participants(db: Session, competition_id: int) -> set[int]:
    """User ids that have tagged at least one ascent with the competition."""
    rows = (
        db.query(ClimbingSession.user_id)
        .join(Ascent, Ascent.session_id == ClimbingSession.id)
        .filter(Ascent.competition_id == competition_id)
        .distinct()
        .all()
    )
    return {row[0] for row in rows}


def participant_users(db: Session, competition_id: int) -> list[User]:
    """Participant users, ordered by username."""
    ids = participants(db, competition_id)
    if not ids:
        return []
    return (
        db.query(User)
        .filter(User.id.in_(ids))
        .order_by(User.username.asc())
        .all()
    )


def active_competition_for_gym(db: Session, gym_id: int) -> Optional[Competition]:
    """The competition available to tag at a gym right now.

    Prefers an event whose window contains today and is active, and that is
    not in a rest week. Falls back to the most recent active event at the gym
    (so the UI can still show the league, letting the date filters decide what
    actually scores).
    """
    today = date.today()
    running_candidates = (
        db.query(Competition)
        .filter(
            Competition.gym_id == gym_id,
            Competition.status == CompetitionStatus.ACTIVE,
            Competition.start_date <= today,
            Competition.end_date >= today,
        )
        .order_by(Competition.start_date.desc())
        .all()
    )
    for competition in running_candidates:
        if not competition.is_rest_week(competition.week_index(today)):
            return competition

    return (
        db.query(Competition)
        .filter(
            Competition.gym_id == gym_id,
            Competition.status == CompetitionStatus.ACTIVE,
        )
        .order_by(Competition.start_date.desc())
        .first()
    )
