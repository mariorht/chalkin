"""
Authentication router - register, login, profile.
"""
import os
import uuid
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.deps import get_current_user
from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserLogin, Token, UserUpdate

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


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.
    """
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
    
    return user


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login and get access token.
    """
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
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
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image (JPEG, PNG, GIF, or WebP)"
        )
    
    # Create directory if it doesn't exist
    os.makedirs(PROFILE_PICS_DIR, exist_ok=True)
    
    # Generate unique filename
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(PROFILE_PICS_DIR, filename)
    
    # Delete old profile picture if exists
    if current_user.profile_picture:
        old_path = os.path.join(PROFILE_PICS_DIR, os.path.basename(current_user.profile_picture))
        if os.path.exists(old_path):
            os.remove(old_path)
    
    # Save new file
    content = await file.read()
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
