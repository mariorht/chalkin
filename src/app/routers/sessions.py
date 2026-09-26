"""
Sessions router - CRUD for climbing sessions.
"""
from typing import List, Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.gym import Gym
from app.models.grade import Grade
from app.models.session import Session as ClimbingSession, ActivityType
from app.models.ascent import Ascent, AscentStatus
from app.models.friendship import Friendship, FriendshipStatus
from app.models.session_exercise import SessionExercise
from app.schemas.session import SessionCreate, SessionResponse, SessionUpdate, SessionWithAscents
from app.schemas.ascent import AscentCreate, AscentResponse
from app.schemas.session_exercise import SessionExerciseCreate, SessionExerciseResponse, SessionExerciseUpdate
from app.models.sense_rep import SenseRep
from app.schemas.sense_rep import SenseRepCreate, SenseRepResponse

router = APIRouter(prefix="/sessions", tags=["Sessions"])


def is_friend(db: Session, user_id: int, other_user_id: int) -> bool:
    """Check if two users are friends."""
    if user_id == other_user_id:
        return True
    friendship = db.query(Friendship).filter(
        or_(
            and_(Friendship.user_id == user_id, Friendship.friend_id == other_user_id),
            and_(Friendship.user_id == other_user_id, Friendship.friend_id == user_id)
        ),
        Friendship.status == FriendshipStatus.ACCEPTED
    ).first()
    return friendship is not None


def enrich_session(session: ClimbingSession, db: Session) -> dict:
    """Add computed fields to a session."""
    # Get gym name and location (home activities have no gym)
    gym = db.query(Gym).filter(Gym.id == session.gym_id).first() if session.gym_id else None
    gym_name = gym.name if gym else "Entrenamiento en casa"
    gym_location = gym.location if gym else None
    activity_type = session.activity_type or ActivityType.GYM
    is_gym = activity_type == ActivityType.GYM
    
    # Count ascents by status
    ascents = db.query(Ascent).filter(Ascent.session_id == session.id).all()
    total_ascents = len(ascents)
    flashes = sum(1 for a in ascents if a.status == AscentStatus.FLASH)
    sends = sum(1 for a in ascents if a.status in [AscentStatus.SEND, AscentStatus.FLASH])
    
    # Get max grade
    max_grade_label = None
    if ascents:
        max_difficulty = 0
        for ascent in ascents:
            if ascent.status != AscentStatus.PROJECT:
                grade = db.query(Grade).filter(Grade.id == ascent.grade_id).first()
                if grade and grade.relative_difficulty > max_difficulty:
                    max_difficulty = grade.relative_difficulty
                    max_grade_label = grade.label
    
    return {
        "id": session.id,
        "user_id": session.user_id,
        "gym_id": session.gym_id,
        "activity_type": activity_type,
        "date": session.date,
        "title": session.title,
        "subtitle": session.subtitle,
        "notes": session.notes,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "strava_activity_id": session.strava_activity_id,
        "gym_name": gym_name,
        "gym_location": gym_location,
        "total_ascents": total_ascents,
        "flashes": flashes,
        "sends": sends,
        "max_grade_label": max_grade_label
    }


@router.get("", response_model=List[SessionResponse])
def list_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    gym_id: Optional[int] = None,
    activity_type: Optional[ActivityType] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List current user's sessions with optional filters.
    """
    query = db.query(ClimbingSession).filter(
        ClimbingSession.user_id == current_user.id
    )
    
    if gym_id:
        query = query.filter(ClimbingSession.gym_id == gym_id)
    
    if activity_type:
        query = query.filter(ClimbingSession.activity_type == activity_type)
    
    if date_from:
        query = query.filter(ClimbingSession.date >= date_from)
    
    if date_to:
        query = query.filter(ClimbingSession.date <= date_to)
    
    sessions = query.order_by(ClimbingSession.date.desc()).offset(skip).limit(limit).all()
    
    # Enrich each session with computed fields
    return [enrich_session(s, db) for s in sessions]


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    session_data: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new session.

    - ``activity_type=gym``: requires ``gym_id`` (climbing at a gym).
    - ``activity_type=home``: ``gym_id`` is ignored/cleared (training at home).
    """
    data = session_data.model_dump()

    if session_data.activity_type == ActivityType.GYM:
        if not session_data.gym_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="gym_id is required for gym activities"
            )
        gym = db.query(Gym).filter(Gym.id == session_data.gym_id).first()
        if not gym:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Gym not found"
            )
    else:
        # Home activities are not tied to a gym.
        data["gym_id"] = None

    session = ClimbingSession(
        user_id=current_user.id,
        **data
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return enrich_session(session, db)


@router.get("/{session_id}", response_model=SessionWithAscents)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific session with all its ascents.
    Users can view their own sessions or sessions from friends.
    """
    session = db.query(ClimbingSession).filter(
        ClimbingSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check if user can view this session (own session or friend's session)
    if session.user_id != current_user.id:
        if not is_friend(db, current_user.id, session.user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own sessions or your friends' sessions"
            )
    
    # Get gym name
    gym = db.query(Gym).filter(Gym.id == session.gym_id).first() if session.gym_id else None
    gym_name = gym.name if gym else "Entrenamiento en casa"
    activity_type = session.activity_type or ActivityType.GYM
    
    # Get session owner username
    session_owner = db.query(User).filter(User.id == session.user_id).first()
    owner_username = session_owner.username if session_owner else "Usuario"
    
    # Calculate summary stats
    ascents = session.ascents
    exercises = session.exercises
    
    return {
        "id": session.id,
        "user_id": session.user_id,
        "gym_id": session.gym_id,
        "activity_type": activity_type,
        "date": session.date,
        "title": session.title,
        "subtitle": session.subtitle,
        "notes": session.notes,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "strava_activity_id": session.strava_activity_id,
        "gym_name": gym_name,
        "ascents": ascents,
        "exercises": exercises,
        "total_ascents": len(ascents),
        "sends": len([a for a in ascents if a.status in [AscentStatus.SEND, AscentStatus.REPEAT]]),
        "flashes": len([a for a in ascents if a.status == AscentStatus.FLASH]),
        "projects": len([a for a in ascents if a.status == AscentStatus.PROJECT]),
        "owner_username": owner_username,
        "is_own": session.user_id == current_user.id
    }


@router.patch("/{session_id}", response_model=SessionResponse)
def update_session(
    session_id: int,
    session_data: SessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a session (e.g., add notes or end time).
    """
    session = db.query(ClimbingSession).filter(
        ClimbingSession.id == session_id,
        ClimbingSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    update_data = session_data.model_dump(exclude_unset=True)
    target_type = update_data.get("activity_type", session.activity_type) or ActivityType.GYM
    target_gym_id = update_data.get("gym_id", session.gym_id)

    if target_type == ActivityType.GYM:
        if not target_gym_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="gym_id is required for gym activities"
            )
        gym = db.query(Gym).filter(Gym.id == target_gym_id).first()
        if not gym:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gym not found")
    else:
        # Switching to a home activity: only allowed if it has no ascents.
        if session.ascents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot convert a session with ascents into a home activity"
            )
        update_data["gym_id"] = None

    for field, value in update_data.items():
        setattr(session, field, value)
    
    db.commit()
    db.refresh(session)
    
    return enrich_session(session, db)


@router.post("/{session_id}/end", response_model=SessionResponse)
def end_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    End a climbing session (set ended_at to now).
    """
    session = db.query(ClimbingSession).filter(
        ClimbingSession.id == session_id,
        ClimbingSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    session.ended_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    
    return enrich_session(session, db)


@router.post("/{session_id}/reopen", response_model=SessionResponse)
def reopen_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reopen a finished climbing session (clear ended_at).
    Useful for editing ascents after accidentally ending a session.
    """
    session = db.query(ClimbingSession).filter(
        ClimbingSession.id == session_id,
        ClimbingSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    session.ended_at = None
    db.commit()
    db.refresh(session)
    
    return enrich_session(session, db)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a session and all its ascents.
    """
    session = db.query(ClimbingSession).filter(
        ClimbingSession.id == session_id,
        ClimbingSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    db.delete(session)
    db.commit()


# Ascents within a session
@router.post("/{session_id}/ascents", response_model=AscentResponse, status_code=status.HTTP_201_CREATED)
def add_ascent(
    session_id: int,
    ascent_data: AscentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add an ascent to a session.
    This is the main action - logging a boulder you climbed!
    """
    session = db.query(ClimbingSession).filter(
        ClimbingSession.id == session_id,
        ClimbingSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Ascents need a gym (grades are gym-scoped). Home activities can't have them.
    if session.gym_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot log ascents in an activity without a gym. Use exercises instead."
        )
    
    # Verify grade exists and belongs to the session's gym
    from app.models.grade import Grade
    grade = db.query(Grade).filter(Grade.id == ascent_data.grade_id).first()
    
    if not grade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grade not found"
        )
    
    if grade.gym_id != session.gym_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Grade does not belong to the session's gym"
        )
    
    ascent = Ascent(
        session_id=session_id,
        **ascent_data.model_dump()
    )
    
    db.add(ascent)
    db.commit()
    db.refresh(ascent)
    
    return ascent


@router.get("/{session_id}/ascents", response_model=List[AscentResponse])
def list_session_ascents(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all ascents in a session.
    Users can view their own sessions or sessions from friends.
    """
    session = db.query(ClimbingSession).filter(
        ClimbingSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check if user can view this session (own session or friend's session)
    if session.user_id != current_user.id:
        if not is_friend(db, current_user.id, session.user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own sessions or your friends' sessions"
            )
    
    return session.ascents


# ===== Session Exercises Endpoints =====

@router.post("/{session_id}/exercises", response_model=SessionExerciseResponse, status_code=status.HTTP_201_CREATED)
def add_exercise_to_session(
    session_id: int,
    exercise: SessionExerciseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a complementary exercise (pullups, campus, etc.) to a session.
    """
    # Verify session exists and belongs to user
    session = db.query(ClimbingSession).filter(ClimbingSession.id == session_id).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only add exercises to your own sessions"
        )
    
    # Create exercise
    db_exercise = SessionExercise(
        session_id=session_id,
        **exercise.model_dump()
    )
    
    db.add(db_exercise)
    db.commit()
    db.refresh(db_exercise)
    
    return db_exercise


@router.get("/{session_id}/exercises", response_model=List[SessionExerciseResponse])
def get_session_exercises(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all exercises for a session.
    """
    # Verify session exists
    session = db.query(ClimbingSession).filter(ClimbingSession.id == session_id).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check if user can view this session (own session or friend's session)
    if session.user_id != current_user.id:
        if not is_friend(db, current_user.id, session.user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own sessions or your friends' sessions"
            )
    
    return session.exercises


@router.put("/exercises/{exercise_id}", response_model=SessionExerciseResponse)
def update_exercise(
    exercise_id: int,
    exercise_update: SessionExerciseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an exercise.
    """
    db_exercise = db.query(SessionExercise).filter(SessionExercise.id == exercise_id).first()
    
    if not db_exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found"
        )
    
    # Verify ownership through session
    session = db.query(ClimbingSession).filter(ClimbingSession.id == db_exercise.session_id).first()
    if not session or session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own exercises"
        )
    
    # Update fields
    for field, value in exercise_update.model_dump(exclude_unset=True).items():
        setattr(db_exercise, field, value)
    
    db.commit()
    db.refresh(db_exercise)
    
    return db_exercise


@router.delete("/exercises/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise(
    exercise_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an exercise.
    """
    db_exercise = db.query(SessionExercise).filter(SessionExercise.id == exercise_id).first()
    
    if not db_exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found"
        )
    
    # Verify ownership through session
    session = db.query(ClimbingSession).filter(ClimbingSession.id == db_exercise.session_id).first()
    if not session or session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own exercises"
        )
    
    db.delete(db_exercise)
    db.commit()
    
    return None


# ===== Chalkin Sense reps (force measurements per exercise) =====

def _get_owned_exercise(db: Session, exercise_id: int, current_user: User) -> SessionExercise:
    """Fetch an exercise verifying it belongs to the current user's session."""
    exercise = db.query(SessionExercise).filter(SessionExercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found"
        )
    session = db.query(ClimbingSession).filter(ClimbingSession.id == exercise.session_id).first()
    if not session or session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage your own exercises"
        )
    return exercise


@router.post(
    "/exercises/{exercise_id}/reps",
    response_model=List[SenseRepResponse],
    status_code=status.HTTP_201_CREATED,
)
def add_sense_reps(
    exercise_id: int,
    reps: List[SenseRepCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Save one or more force reps measured with Chalkin Sense for an exercise.

    The client records a set of reps and posts them in bulk.
    """
    exercise = _get_owned_exercise(db, exercise_id, current_user)

    created = []
    for index, rep in enumerate(reps, start=1):
        data = rep.model_dump()
        # Defaults for optional fields
        data.setdefault("source", "sense")
        if data.get("rep_index") is None:
            data["rep_index"] = index
        db_rep = SenseRep(
            exercise_id=exercise.id,
            session_id=exercise.session_id,
            **data,
        )
        db.add(db_rep)
        created.append(db_rep)

    db.commit()
    for rep in created:
        db.refresh(rep)

    return created


@router.get("/exercises/{exercise_id}/reps", response_model=List[SenseRepResponse])
def list_sense_reps(
    exercise_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List the force reps of an exercise. Owners and friends can view them.
    """
    exercise = db.query(SessionExercise).filter(SessionExercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found"
        )
    session = db.query(ClimbingSession).filter(ClimbingSession.id == exercise.session_id).first()
    if session and session.user_id != current_user.id:
        if not is_friend(db, current_user.id, session.user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own sessions or your friends' sessions"
            )
    return (
        db.query(SenseRep)
        .filter(SenseRep.exercise_id == exercise_id)
        .order_by(SenseRep.set_index, SenseRep.rep_index)
        .all()
    )


@router.delete("/reps/{rep_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sense_rep(
    rep_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a single force rep."""
    rep = db.query(SenseRep).filter(SenseRep.id == rep_id).first()
    if not rep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rep not found"
        )
    _get_owned_exercise(db, rep.exercise_id, current_user)
    db.delete(rep)
    db.commit()
    return None
