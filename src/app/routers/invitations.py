"""
Invitations router - for invitation-only registration system.
"""
import secrets
from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.invitation import Invitation
from app.schemas.invitation import InvitationCreate, InvitationResponse, InvitationLink

router = APIRouter(prefix="/invitations", tags=["Invitations"])


@router.post("/generate", response_model=InvitationLink, status_code=status.HTTP_201_CREATED)
def generate_invitation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a new invitation link valid for 24 hours.
    Only authenticated users can generate invitations.
    """
    # Generate a secure random token
    token = secrets.token_urlsafe(32)
    
    # Set expiry to 24 hours from now
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    # Create invitation
    invitation = Invitation(
        token=token,
        created_by_user_id=current_user.id,
        expires_at=expires_at,
        used=False
    )
    
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    
    # Build the full invitation link
    # Note: In production, you might want to get the base URL from config
    invitation_link = f"/register?invitation={token}"
    
    return InvitationLink(
        token=token,
        expires_at=expires_at,
        link=invitation_link
    )


@router.get("/validate/{token}", response_model=dict)
def validate_invitation(token: str, db: Session = Depends(get_db)):
    """
    Validate if an invitation token is valid and unused.
    Returns basic info about the invitation status.
    """
    invitation = db.query(Invitation).filter(Invitation.token == token).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    # Check if already used
    if invitation.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has already been used"
        )
    
    # Check if expired
    if datetime.utcnow() > invitation.expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired"
        )
    
    return {
        "valid": True,
        "expires_at": invitation.expires_at.isoformat()
    }


@router.get("/my-invitations", response_model=List[InvitationResponse])
def get_my_invitations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all invitations created by the current user.
    """
    invitations = db.query(Invitation).filter(
        Invitation.created_by_user_id == current_user.id
    ).order_by(Invitation.created_at.desc()).all()
    
    return invitations
