"""
Grades router - CRUD for gym grades/difficulty levels.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.core.deps import get_current_user
from app.core.permissions import can_edit_gym
from app.models.user import User
from app.models.gym import Gym
from app.models.grade import Grade
from app.schemas.grade import GradeCreate, GradeResponse, GradeUpdate, BulkGradeCreate

router = APIRouter(prefix="/grades", tags=["Grades"])


def _require_editable_gym(user: User, gym: Gym) -> None:
    """Grades are part of a gym's configuration, so the gym rule applies."""
    if not can_edit_gym(user, gym):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This gym is verified: only admins can edit its grades",
        )


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

    _require_editable_gym(current_user, gym)
    
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

    gym = db.query(Gym).filter(Gym.id == grade.gym_id).first()
    _require_editable_gym(current_user, gym)
    
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

    Refused while ascents reference it: deleting a grade cascades to those
    ascents, which would silently destroy climbing history.
    """
    grade = db.query(Grade).filter(Grade.id == grade_id).first()
    
    if not grade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grade not found"
        )

    gym = db.query(Gym).filter(Gym.id == grade.gym_id).first()
    _require_editable_gym(current_user, gym)

    from app.models.ascent import Ascent

    in_use = db.query(Ascent).filter(Ascent.grade_id == grade.id).count()
    if in_use:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"This grade is used by {in_use} ascent(s); "
                "it cannot be deleted without losing history"
            ),
        )
    
    db.delete(grade)
    db.commit()


@router.post("/bulk", response_model=List[GradeResponse], status_code=status.HTTP_201_CREATED)
def create_grades_bulk(
    bulk_data: BulkGradeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create multiple grades at once (useful for setting up a new gym).
    """
    if not bulk_data.grades:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No grades provided"
        )
    
    # Verify gym exists
    gym = db.query(Gym).filter(Gym.id == bulk_data.gym_id).first()
    if not gym:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gym not found"
        )

    _require_editable_gym(current_user, gym)
    
    grades = [
        Grade(gym_id=bulk_data.gym_id, **g.model_dump()) 
        for g in bulk_data.grades
    ]
    db.add_all(grades)
    db.commit()
    
    for grade in grades:
        db.refresh(grade)
    
    return grades
