"""
Admin router - user lookup and password reset link generation.

Admins cannot set passwords directly; they generate a single-use reset link and
deliver it to the user themselves (no email service required).
"""
import secrets
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.core.deps import get_current_admin
from app.core.security import hash_token
from app.models.user import User
from app.models.password_reset import PasswordResetToken
from app.schemas.admin import AdminUserResult, PasswordResetLink

router = APIRouter(prefix="/admin", tags=["Admin"])

# Reset links are short-lived compared to invitations
RESET_TOKEN_TTL_MINUTES = 60


@router.get("/me", response_model=AdminUserResult)
def admin_me(current_admin: User = Depends(get_current_admin)):
    """Return the current admin. Used by the admin page to gate access."""
    return current_admin


@router.get("/users", response_model=List[AdminUserResult])
def search_users(
    q: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Search users by username or email (admin only)."""
    limit = max(1, min(limit, 50))
    query = db.query(User)

    if q:
        term = f"%{q.strip()}%"
        query = query.filter(or_(User.username.ilike(term), User.email.ilike(term)))

    return query.order_by(User.created_at.desc()).limit(limit).all()


@router.post("/users/{user_id}/password-reset", response_model=PasswordResetLink)
def create_password_reset(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """
    Generate a single-use password reset link for a user.

    Any previous unused reset tokens for that user are invalidated.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    now = datetime.utcnow()

    # Invalidate any outstanding unused tokens for this user
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used == False,  # noqa: E712
    ).update({"used": True, "used_at": now}, synchronize_session=False)

    token = secrets.token_urlsafe(32)
    expires_at = now + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)

    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(token),
        created_by_user_id=current_admin.id,
        expires_at=expires_at,
        used=False,
    )
    db.add(reset_token)
    db.commit()
    db.refresh(reset_token)

    reset_path = f"/reset-password?token={token}"
    email_subject = "Restablece tu contraseña de Chalkin"
    email_body = (
        f"Hola {user.username},\n\n"
        "Hemos generado un enlace para restablecer la contraseña de tu cuenta "
        "en Chalkin. Puedes crear una nueva contraseña desde aquí:\n\n"
        "{link}\n\n"
        f"El enlace es válido durante {RESET_TOKEN_TTL_MINUTES} minutos y solo "
        "puede usarse una vez.\n\n"
        "Si no has solicitado este cambio, ignora este mensaje.\n\n"
        "Saludos,\nEl equipo de Chalkin"
    )

    return PasswordResetLink(
        reset_path=reset_path,
        token=token,
        expires_at=expires_at,
        email_subject=email_subject,
        email_body=email_body,
    )
