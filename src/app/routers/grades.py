"""
Grades router - CRUD for gym grades/difficulty levels.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.gym import Gym
from app.models.grade import Grade
from app.schemas.grade import GradeCreate, GradeResponse, GradeUpdate

router = APIRouter(prefix="/grades", tags=["Grades"])


@router.post("", response_model=GradeResponse, status_code=status.HTTP_201_CREATED)
def create_grade(
    grade_data: GradeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new grade for a gym.
    """
    # Verify gym exists
    gym = db.query(Gym).filter(Gym.id == grade_data.gym_id).first()
    if not gym:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gym not found"
        )
    
    grade = Grade(**grade_data.model_dump())
    db.add(grade)
    db.commit()
    db.refresh(grade)
    
    return grade


@router.get("/{grade_id}", response_model=GradeResponse)
def get_grade(grade_id: int, db: Session = Depends(get_db)):
    """
    Get a specific grade.
    """
    grade = db.query(Grade).filter(Grade.id == grade_id).first()
    
    if not grade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grade not found"
        )
    
    return grade


@router.patch("/{grade_id}", response_model=GradeResponse)
def update_grade(
    grade_id: int,
    grade_data: GradeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a grade.
    """
    grade = db.query(Grade).filter(Grade.id == grade_id).first()
    
    if not grade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grade not found"
        )
    
    update_data = grade_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(grade, field, value)
    
    db.commit()
    db.refresh(grade)
    
    return grade


@router.delete("/{grade_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_grade(
    grade_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a grade.
    """
    grade = db.query(Grade).filter(Grade.id == grade_id).first()
    
    if not grade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grade not found"
        )
    
    db.delete(grade)
    db.commit()


@router.post("/bulk", response_model=List[GradeResponse], status_code=status.HTTP_201_CREATED)
def create_grades_bulk(
    grades_data: List[GradeCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create multiple grades at once (useful for setting up a new gym).
    """
    if not grades_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No grades provided"
        )
    
    # Verify all gyms exist
    gym_ids = set(g.gym_id for g in grades_data)
    for gym_id in gym_ids:
        gym = db.query(Gym).filter(Gym.id == gym_id).first()
        if not gym:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Gym with id {gym_id} not found"
            )
    
    grades = [Grade(**g.model_dump()) for g in grades_data]
    db.add_all(grades)
    db.commit()
    
    for grade in grades:
        db.refresh(grade)
    
    return grades
