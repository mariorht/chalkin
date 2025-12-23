"""
User schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    """Base user schema with common fields."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=6, max_length=100)
    home_gym_id: Optional[int] = None


class UserUpdate(BaseModel):
    """Schema for updating user info."""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    home_gym_id: Optional[int] = None
    password: Optional[str] = Field(None, min_length=6, max_length=100)


class UserResponse(UserBase):
    """Schema for user responses (no password)."""
    id: int
    home_gym_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    """Schema for login request."""
    email: EmailStr
    password: str


class TokenUser(BaseModel):
    """User info included in token response."""
    id: int
    username: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user: Optional[TokenUser] = None


class TokenData(BaseModel):
    """Schema for decoded token data."""
    user_id: Optional[int] = None
