"""
Sessions router - CRUD for climbing sessions.
"""
from typing import List, Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.gym import Gym
from app.models.session import Session as ClimbingSession
from app.models.ascent import Ascent, AscentStatus
from app.schemas.session import SessionCreate, SessionResponse, SessionUpdate, SessionWithAscents
from app.schemas.ascent import AscentCreate, AscentResponse

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.get("", response_model=List[SessionResponse])
def list_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    gym_id: Optional[int] = None,
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
    
    if date_from:
        query = query.filter(ClimbingSession.date >= date_from)
    
    if date_to:
        query = query.filter(ClimbingSession.date <= date_to)
    
    sessions = query.order_by(ClimbingSession.date.desc()).offset(skip).limit(limit).all()
    return sessions


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    session_data: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new climbing session (check-in to a gym).
    """
    # Verify gym exists
    gym = db.query(Gym).filter(Gym.id == session_data.gym_id).first()
    if not gym:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gym not found"
        )
    
    session = ClimbingSession(
        user_id=current_user.id,
        **session_data.model_dump()
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return session


@router.get("/{session_id}", response_model=SessionWithAscents)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific session with all its ascents.
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
    
    # Calculate summary stats
    ascents = session.ascents
    response = SessionWithAscents.model_validate(session)
    response.total_ascents = len(ascents)
    response.sends = len([a for a in ascents if a.status in [AscentStatus.SEND, AscentStatus.REPEAT]])
    response.flashes = len([a for a in ascents if a.status == AscentStatus.FLASH])
    response.projects = len([a for a in ascents if a.status == AscentStatus.PROJECT])
    
    return response


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
    for field, value in update_data.items():
        setattr(session, field, value)
    
    db.commit()
    db.refresh(session)
    
    return session


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


@router.post("/{session_id}/end", response_model=SessionResponse)
def end_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    End a session (sets ended_at to now).
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
    
    return session


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
    
    return session.ascents
