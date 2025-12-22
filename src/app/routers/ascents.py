"""
Ascents router - CRUD for individual ascents.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.ascent import Ascent
from app.models.session import Session as ClimbingSession
from app.schemas.ascent import AscentResponse, AscentUpdate

router = APIRouter(prefix="/ascents", tags=["Ascents"])


@router.get("/{ascent_id}", response_model=AscentResponse)
def get_ascent(
    ascent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific ascent.
    """
    ascent = db.query(Ascent).join(ClimbingSession).filter(
        Ascent.id == ascent_id,
        ClimbingSession.user_id == current_user.id
    ).first()
    
    if not ascent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ascent not found"
        )
    
    return ascent


@router.patch("/{ascent_id}", response_model=AscentResponse)
def update_ascent(
    ascent_id: int,
    ascent_data: AscentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an ascent.
    """
    ascent = db.query(Ascent).join(ClimbingSession).filter(
        Ascent.id == ascent_id,
        ClimbingSession.user_id == current_user.id
    ).first()
    
    if not ascent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ascent not found"
        )
    
    # If updating grade_id, verify it belongs to the session's gym
    if ascent_data.grade_id:
        from app.models.grade import Grade
        grade = db.query(Grade).filter(Grade.id == ascent_data.grade_id).first()
        
        if not grade:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Grade not found"
            )
        
        if grade.gym_id != ascent.session.gym_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Grade does not belong to the session's gym"
            )
    
    update_data = ascent_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ascent, field, value)
    
    db.commit()
    db.refresh(ascent)
    
    return ascent


@router.delete("/{ascent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ascent(
    ascent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an ascent.
    """
    ascent = db.query(Ascent).join(ClimbingSession).filter(
        Ascent.id == ascent_id,
        ClimbingSession.user_id == current_user.id
    ).first()
    
    if not ascent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ascent not found"
        )
    
    db.delete(ascent)
    db.commit()
