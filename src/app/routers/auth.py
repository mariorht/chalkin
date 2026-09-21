"""
Authentication router - register, login, profile.
"""
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, hash_token
from app.core.deps import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.invitation import Invitation
from app.models.password_reset import PasswordResetToken
from app.schemas.user import UserCreate, UserResponse, UserLogin, Token, UserUpdate
from app.schemas.admin import PasswordResetRequest, PasswordResetResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Directory for profile pictures (inside data_dir for persistence)
# With fallback to app/uploads if data_dir is not writable
_data_dir = os.path.abspath(settings.data_dir)
_base_dir = os.path.dirname(os.path.abspath(__file__))
try:
    _test_dir = os.path.join(_data_dir, "uploads", "profiles")
    os.makedirs(_test_dir, exist_ok=True)
    PROFILE_PICS_DIR = _test_dir
except PermissionError:
    PROFILE_PICS_DIR = os.path.join(os.path.dirname(_base_dir), "uploads", "profiles")
    os.makedirs(PROFILE_PICS_DIR, exist_ok=True)

# Canonical image MIME types we accept, mapped to the extension we store.
_ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}


def detect_image_type(content: bytes) -> Optional[str]:
    """Detect the real image type from magic bytes (never trust the client)."""
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


# Valid bcrypt hash used to equalize login timing for unknown emails.
_DUMMY_PASSWORD_HASH = get_password_hash("chalkin-dummy-password")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.
    Requires a valid invitation token.
    """
    # Validate invitation token
    if not user_data.invitation_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation token is required for registration"
        )
    
    invitation = db.query(Invitation).filter(
        Invitation.token == user_data.invitation_token
    ).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invitation token"
        )
    
    # Check if invitation has been used
    if invitation.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invitation has already been used"
        )
    
    # Check if invitation has expired
    if datetime.utcnow() > invitation.expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invitation has expired"
        )
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username already exists
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create user
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        home_gym_id=user_data.home_gym_id
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Mark invitation as used
    invitation.used = True
    invitation.used_by_user_id = user.id
    invitation.used_at = datetime.utcnow()
    db.commit()
    
    return user


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login and get access token.
    """
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user:
        # Run a dummy hash verification so the response time does not reveal
        # whether the email exists (user enumeration via timing).
        verify_password(credentials.password, _DUMMY_PASSWORD_HASH)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    
    return Token(
        access_token=access_token,
        user={"id": user.id, "username": user.username, "email": user.email, "profile_picture": user.profile_picture}
    )


@router.post("/reset-password", response_model=PasswordResetResponse)
def reset_password(data: PasswordResetRequest, db: Session = Depends(get_db)):
    """
    Set a new password using a single-use reset token generated by an admin.
    """
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == hash_token(data.token)
    ).first()

    if not reset_token or reset_token.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already used reset link"
        )

    if datetime.utcnow() > reset_token.expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset link has expired"
        )

    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset link"
        )

    now = datetime.utcnow()
    user.password_hash = get_password_hash(data.new_password)
    # Invalidate any JWT issued before this change
    user.password_changed_at = now

    reset_token.used = True
    reset_token.used_at = now

    db.commit()

    return PasswordResetResponse()


@router.get("/me", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    """
    Get current user's profile.
    """
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile.
    """
    # Check for unique constraints if updating
    if user_data.email and user_data.email != current_user.email:
        existing = db.query(User).filter(User.email == user_data.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    if user_data.username and user_data.username != current_user.username:
        existing = db.query(User).filter(User.username == user_data.username).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Update fields
    update_data = user_data.model_dump(exclude_unset=True)
    
    if "password" in update_data:
        update_data["password_hash"] = get_password_hash(update_data.pop("password"))
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.post("/me/picture", response_model=UserResponse)
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a profile picture.
    """
    # Read with a hard size cap to avoid memory exhaustion.
    content = await file.read(settings.max_file_size + 1)
    if len(content) > settings.max_file_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large (max {settings.max_file_size} bytes)"
        )
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file"
        )

    # Determine the real type from the file contents, never from the client.
    detected_type = detect_image_type(content)
    if detected_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a valid image (JPEG, PNG, GIF, or WebP)"
        )

    # The declared type must match the actual content type.
    if file.content_type != detected_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match its declared type"
        )

    # Create directory if it doesn't exist
    os.makedirs(PROFILE_PICS_DIR, exist_ok=True)

    # Extension is derived from the detected type, never from the filename.
    ext = _ALLOWED_IMAGE_TYPES[detected_type]
    filename = f"{current_user.id}_{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(PROFILE_PICS_DIR, filename)
    
    # Delete old profile picture if exists
    if current_user.profile_picture:
        old_path = os.path.join(PROFILE_PICS_DIR, os.path.basename(current_user.profile_picture))
        if os.path.exists(old_path):
            os.remove(old_path)
    
    # Save new file
    with open(filepath, "wb") as f:
        f.write(content)
    
    # Update user
    current_user.profile_picture = f"/data/uploads/profiles/{filename}"
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.delete("/me/picture", response_model=UserResponse)
def delete_profile_picture(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete profile picture.
    """
    if current_user.profile_picture:
        # Delete file
        filepath = os.path.join(PROFILE_PICS_DIR, os.path.basename(current_user.profile_picture))
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # Clear from database
        current_user.profile_picture = None
        db.commit()
        db.refresh(current_user)
    
    return current_user
