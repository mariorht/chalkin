"""
Gyms router - CRUD for climbing gyms.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.core.deps import get_current_user, get_optional_user
from app.models.user import User
from app.models.gym import Gym
from app.models.grade import Grade
from app.schemas.gym import GymCreate, GymResponse, GymUpdate, GymWithGrades
from app.schemas.grade import GradeResponse

router = APIRouter(prefix="/gyms", tags=["Gyms"])


@router.get("", response_model=List[GymResponse])
def list_gyms(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all gyms, optionally filtered by search term.
    """
    query = db.query(Gym)
    
    if search:
        query = query.filter(
            Gym.name.ilike(f"%{search}%") | 
            Gym.location.ilike(f"%{search}%")
        )
    
    gyms = query.offset(skip).limit(limit).all()
    return gyms


@router.post("", response_model=GymResponse, status_code=status.HTTP_201_CREATED)
def create_gym(
    gym_data: GymCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new gym.
    """
    gym = Gym(**gym_data.model_dump())
    db.add(gym)
    db.commit()
    db.refresh(gym)
    return gym


@router.get("/{gym_id}", response_model=GymWithGrades)
def get_gym(gym_id: int, db: Session = Depends(get_db)):
    """
    Get a specific gym with its grades.
    """
    gym = db.query(Gym).filter(Gym.id == gym_id).first()
    
    if not gym:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gym not found"
        )
    
    return gym


@router.patch("/{gym_id}", response_model=GymResponse)
def update_gym(
    gym_id: int,
    gym_data: GymUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a gym's information.
    """
    gym = db.query(Gym).filter(Gym.id == gym_id).first()
    
    if not gym:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gym not found"
        )
    
    update_data = gym_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(gym, field, value)
    
    db.commit()
    db.refresh(gym)
    
    return gym


@router.delete("/{gym_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_gym(
    gym_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a gym.
    """
    gym = db.query(Gym).filter(Gym.id == gym_id).first()
    
    if not gym:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gym not found"
        )
    
    db.delete(gym)
    db.commit()


@router.get("/{gym_id}/grades", response_model=List[GradeResponse])
def get_gym_grades(gym_id: int, db: Session = Depends(get_db)):
    """
    Get all grades for a specific gym, ordered by difficulty.
    """
    gym = db.query(Gym).filter(Gym.id == gym_id).first()
    
    if not gym:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gym not found"
        )
    
    grades = db.query(Grade).filter(
        Grade.gym_id == gym_id
    ).order_by(Grade.order, Grade.relative_difficulty).all()
    
    return grades
