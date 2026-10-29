"""
Grades router - CRUD for gym grades/difficulty levels.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.core.deps import get_current_user, get_current_admin
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


def _label_key(label: str) -> str:
    """Comparison key for grade labels: trimmed and case-insensitive."""
    return (label or "").strip().casefold()


def _find_duplicate(
    db: Session, gym_id: int, label: str, exclude_id: Optional[int] = None
) -> Optional[Grade]:
    """Find a grade of the same gym with an equivalent label.

    SQLite's lower() does not fold accents, so compare in Python. A gym has a
    handful of grades, so this is cheap.
    """
    key = _label_key(label)
    if not key:
        return None

    for grade in db.query(Grade).filter(Grade.gym_id == gym_id).all():
        if exclude_id is not None and grade.id == exclude_id:
            continue
        if _label_key(grade.label) == key:
            return grade
    return None


def _reject_duplicate(db: Session, gym_id: int, label: str, exclude_id: Optional[int] = None) -> None:
    dup = _find_duplicate(db, gym_id, label, exclude_id=exclude_id)
    if dup is None:
        return
    if dup.is_active:
        detail = f'Ya existe un grado con el nombre "{dup.label}" en este gimnasio'
    else:
        detail = (
            f'Ya existe un grado archivado con el nombre "{dup.label}"; '
            "un administrador puede restaurarlo"
        )
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


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

    data = grade_data.model_dump()
    data["label"] = data["label"].strip()
    if not data["label"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre del grado no puede estar vacío",
        )
    _reject_duplicate(db, gym.id, data["label"])

    grade = Grade(**data)
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

    if update_data.get("label") is not None:
        update_data["label"] = update_data["label"].strip()
        if not update_data["label"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre del grado no puede estar vacío",
            )
        _reject_duplicate(
            db, grade.gym_id, update_data["label"], exclude_id=grade.id
        )

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
    from app.models.competition import CompetitionPoint

    ascents = db.query(Ascent).filter(Ascent.grade_id == grade.id).count()
    points = db.query(CompetitionPoint).filter(
        CompetitionPoint.grade_id == grade.id
    ).count()

    if ascents or points:
        # Keep the row so historical ascents and league points still resolve
        # their label and colour; just hide it from new activity.
        grade.is_active = False
        db.commit()
        return

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

    rows = []
    seen = set()
    for item in bulk_data.grades:
        row = item.model_dump()
        row["label"] = row["label"].strip()
        if not row["label"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre de un grado no puede estar vacío",
            )

        key = _label_key(row["label"])
        if key in seen:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'El grado "{row["label"]}" está repetido en la lista',
            )
        seen.add(key)

        _reject_duplicate(db, bulk_data.gym_id, row["label"])
        rows.append(row)

    grades = [
        Grade(gym_id=bulk_data.gym_id, **row)
        for row in rows
    ]
    db.add_all(grades)
    db.commit()
    
    for grade in grades:
        db.refresh(grade)
    
    return grades


@router.post("/{grade_id}/restore", response_model=GradeResponse)
def restore_grade(
    grade_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """
    Restore an archived grade (admin only).

    It becomes selectable again for new ascents; the history that already
    used it keeps pointing to the same row.
    """
    grade = db.query(Grade).filter(Grade.id == grade_id).first()

    if not grade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grade not found",
        )

    if grade.is_active:
        return grade

    _reject_duplicate(db, grade.gym_id, grade.label, exclude_id=grade.id)

    grade.is_active = True
    db.commit()
    db.refresh(grade)

    return grade
