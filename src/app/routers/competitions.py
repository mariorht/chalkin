"""
Competitions router - league events, tagging and leaderboards.

- Admins create/configure competitions and their points per grade.
- Any user can list the competitions they can tag (running at a gym).
- The leaderboard is visible to everyone participating in the event.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.core.deps import get_current_user, get_optional_user
from app.models.user import User
from app.models.gym import Gym
from app.models.grade import Grade
from app.models.competition import Competition, CompetitionPoint, CompetitionStatus
from app.schemas.competition import (
    CompetitionCreate,
    CompetitionResponse,
    CompetitionUpdate,
    CompetitionPointResponse,
    CompetitionWeekResponse,
    CompetitionLeaderboard,
    LeaderboardEntry,
    GradeBreakdown,
)
from app.services import competition as comp_service

router = APIRouter(prefix="/competitions", tags=["Competitions"])


def _serialize(db: Session, competition: Competition) -> CompetitionResponse:
    """Build a CompetitionResponse with display info for its points."""
    points: List[CompetitionPointResponse] = []
    rows = (
        db.query(CompetitionPoint, Grade)
        .join(Grade, CompetitionPoint.grade_id == Grade.id)
        .filter(CompetitionPoint.competition_id == competition.id)
        .order_by(Grade.order.asc(), Grade.relative_difficulty.asc())
        .all()
    )
    for point, grade in rows:
        points.append(
            CompetitionPointResponse(
                id=point.id,
                grade_id=grade.id,
                points=point.points,
                label=grade.label,
                color_hex=grade.color_hex,
                relative_difficulty=grade.relative_difficulty,
            )
        )

    gym = db.query(Gym).filter(Gym.id == competition.gym_id).first()
    return CompetitionResponse(
        id=competition.id,
        gym_id=competition.gym_id,
        gym_name=gym.name if gym else None,
        name=competition.name,
        description=competition.description,
        start_date=competition.start_date,
        end_date=competition.end_date,
        status=competition.status,
        is_running=competition.is_running,
        total_weeks=competition.total_weeks,
        week_offsets=sorted(competition.offset_weeks),
        points=points,
        created_at=competition.created_at,
        updated_at=competition.updated_at,
    )


def _is_participant(db: Session, competition_id: int, user_id: int) -> bool:
    return user_id in comp_service.participants(db, competition_id)


@router.get("", response_model=List[CompetitionResponse])
def list_competitions(
    gym_id: Optional[int] = None,
    only_active: bool = False,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """List competitions (optionally filtered by gym). Non-admins see published ones."""
    query = db.query(Competition)
    if gym_id is not None:
        query = query.filter(Competition.gym_id == gym_id)
    if only_active or not (current_user and current_user.is_admin):
        # Draft competitions are only visible to admins
        query = query.filter(Competition.status != CompetitionStatus.DRAFT)

    query = query.order_by(Competition.start_date.desc(), Competition.name.asc())
    return [_serialize(db, c) for c in query.all()]


@router.get("/running", response_model=Optional[CompetitionResponse])
def running_competition(
    gym_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    The competition available to tag at a gym right now.

    Used by the session detail page to decide whether to offer the league
    toggle. Returns ``null`` when there is none.
    """
    competition = comp_service.active_competition_for_gym(db, gym_id)
    if not competition:
        return None
    return _serialize(db, competition)


@router.post("", response_model=CompetitionResponse, status_code=status.HTTP_201_CREATED)
def create_competition(
    data: CompetitionCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_user),
):
    """Create a competition and its points (admin only)."""
    if not current_admin.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")

    gym = db.query(Gym).filter(Gym.id == data.gym_id).first()
    if not gym:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gym not found")

    if data.end_date < data.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be on or after start_date",
        )

    competition = Competition(
        gym_id=data.gym_id,
        name=data.name,
        description=data.description,
        start_date=data.start_date,
        end_date=data.end_date,
        status=CompetitionStatus(data.status.value),
    )
    competition.set_offset_weeks(data.week_offsets)
    db.add(competition)
    db.flush()

    _replace_points(db, competition, data.gym_id, data.points)

    db.commit()
    db.refresh(competition)
    return _serialize(db, competition)


@router.get("/{competition_id}", response_model=CompetitionResponse)
def get_competition(
    competition_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Get a competition with its points."""
    competition = db.query(Competition).filter(Competition.id == competition_id).first()
    if not competition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competition not found")
    if competition.status == CompetitionStatus.DRAFT and not (
        current_user and current_user.is_admin
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competition not found")
    return _serialize(db, competition)


@router.patch("/{competition_id}", response_model=CompetitionResponse)
def update_competition(
    competition_id: int,
    data: CompetitionUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_user),
):
    """Update a competition (admin only)."""
    if not current_admin.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")

    competition = db.query(Competition).filter(Competition.id == competition_id).first()
    if not competition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competition not found")

    update_data = data.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"] is not None:
        update_data["status"] = CompetitionStatus(update_data["status"].value)

    # week_offsets is stored as a compact string, not a column value
    offsets = update_data.pop("week_offsets", None)

    start = update_data.get("start_date", competition.start_date)
    end = update_data.get("end_date", competition.end_date)
    if end < start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be on or after start_date",
        )

    for field, value in update_data.items():
        setattr(competition, field, value)

    if offsets is not None:
        competition.set_offset_weeks(offsets)

    db.commit()
    db.refresh(competition)
    return _serialize(db, competition)


@router.put("/{competition_id}/points", response_model=CompetitionResponse)
def set_points(
    competition_id: int,
    points: List[dict],
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_user),
):
    """Replace the whole points table of a competition (admin only).

    Body: a list of ``{"grade_id": int, "points": int}``.
    """
    if not current_admin.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")

    competition = db.query(Competition).filter(Competition.id == competition_id).first()
    if not competition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competition not found")

    from app.schemas.competition import CompetitionPointItem

    parsed = [CompetitionPointItem(**item) for item in points]
    _replace_points(db, competition, competition.gym_id, parsed)

    db.commit()
    db.refresh(competition)
    return _serialize(db, competition)


@router.delete("/{competition_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_competition(
    competition_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_user),
):
    """Delete a competition (admin only)."""
    if not current_admin.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")

    competition = db.query(Competition).filter(Competition.id == competition_id).first()
    if not competition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competition not found")

    db.delete(competition)
    db.commit()


@router.get("/{competition_id}/leaderboard", response_model=CompetitionLeaderboard)
def leaderboard(
    competition_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Leaderboard for a competition, visible to participants.

    Includes everyone who has tagged at least one league boulder. Non
    participants get a 403 so the standings stay within the event.
    """
    competition = db.query(Competition).filter(Competition.id == competition_id).first()
    if not competition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competition not found")

    participant_ids = comp_service.participants(db, competition_id)
    if current_user.id not in participant_ids and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only participants can see the leaderboard",
        )

    users = {u.id: u for u in comp_service.participant_users(db, competition_id)}
    data = comp_service.standings(db, competition)
    overall = data["overall"]
    weekly = data["weekly"]

    # Grade info for the breakdown (label/colour) and points per grade
    grades = {
        g.id: g
        for g in db.query(Grade).filter(Grade.gym_id == competition.gym_id).all()
    }
    points_by_grade = comp_service.competition_points_map(db, competition.id)

    def breakdown_for(values: dict) -> List[GradeBreakdown]:
        items = []
        for grade_id, info in values.get("by_grade", {}).items():
            grade = grades.get(grade_id)
            count = info["count"]
            # Block numbers, sorted by (week, block). Legacy rows without a
            # block number simply produce an empty list.
            blocks = sorted(
                (week, block)
                for week, nums in info.get("blocks", {}).items()
                for block in nums
            )
            items.append(
                GradeBreakdown(
                    grade_id=grade_id,
                    label=grade.label if grade else None,
                    color_hex=grade.color_hex if grade else None,
                    count=count,
                    points=points_by_grade.get(grade_id, 0) * count,
                    blocks=[block for _, block in blocks],
                )
            )
        # Hardest grades first (by points per boulder, then count)
        items.sort(key=lambda b: (-b.points, b.label or ""))
        return items

    def entries_for(bucket: dict[int, dict], with_breakdown: bool = False) -> List[LeaderboardEntry]:
        entries = []
        for user_id, values in bucket.items():
            user = users.get(user_id)
            if user is None:
                continue
            entries.append(
                LeaderboardEntry(
                    user_id=user_id,
                    username=user.username,
                    profile_picture=user.profile_picture,
                    points=values["points"],
                    scored_boulders=len(values["scored"]),
                    is_me=user_id == current_user.id,
                    breakdown=breakdown_for(values) if with_breakdown else [],
                )
            )
        entries.sort(key=lambda e: (-e.points, -e.scored_boulders, e.username.lower()))
        return entries

    gym = db.query(Gym).filter(Gym.id == competition.gym_id).first()

    weeks: List[CompetitionWeekResponse] = []
    weekly_entries: List[List[LeaderboardEntry]] = []
    today = competition_week_today(competition)
    for week in range(1, competition.total_weeks + 1):
        start, end = competition.week_bounds(week)
        weeks.append(
            CompetitionWeekResponse(
                week=week,
                start_date=start,
                end_date=end,
                is_current=(today == week),
                is_rest=competition.is_rest_week(week),
            )
        )
        weekly_entries.append(entries_for(weekly.get(week, {})))

    return CompetitionLeaderboard(
        competition_id=competition.id,
        competition_name=competition.name,
        gym_name=gym.name if gym else None,
        status=competition.status,
        weeks=weeks,
        weekly=weekly_entries,
        total=entries_for(overall, with_breakdown=True),
    )


def competition_week_today(competition: Competition) -> int:
    """Week number of today within the competition (0 if outside)."""
    from datetime import date as _date

    return competition.week_index(_date.today())


def _replace_points(db: Session, competition: Competition, gym_id: int, points) -> None:
    """Replace all points of a competition, validating grades belong to the gym."""
    db.query(CompetitionPoint).filter(
        CompetitionPoint.competition_id == competition.id
    ).delete(synchronize_session=False)

    for item in points:
        grade = db.query(Grade).filter(Grade.id == item.grade_id).first()
        if not grade or grade.gym_id != gym_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Grade {item.grade_id} does not belong to the competition's gym",
            )
        db.add(
            CompetitionPoint(
                competition_id=competition.id,
                grade_id=item.grade_id,
                points=item.points,
            )
        )
