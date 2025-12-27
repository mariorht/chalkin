"""
Strava OAuth router - Handle authorization and token exchange.
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import httpx

from app.core.config import settings
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.strava_connection import StravaConnection


router = APIRouter(prefix="/strava", tags=["strava"])


@router.get("/connect")
async def connect_strava(current_user: User = Depends(get_current_user)):
    """
    Initiate Strava OAuth flow.
    Returns the authorization URL for the frontend to redirect.
    """
    if not settings.strava_client_id or not settings.strava_redirect_uri:
        raise HTTPException(status_code=500, detail="Strava not configured")
    
    # Build authorization URL
    auth_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={settings.strava_client_id}"
        f"&response_type=code"
        f"&redirect_uri={settings.strava_redirect_uri}"
        f"&approval_prompt=auto"
        f"&scope=activity:write,read"
        f"&state={current_user.id}"  # Use user_id as state for security
    )
    
    return {"auth_url": auth_url}


@router.get("/callback")
async def strava_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback from Strava.
    Exchange the authorization code for access and refresh tokens.
    """
    if error:
        # User denied authorization or error occurred
        return RedirectResponse(url="/static/templates/profile.html?strava_error=denied")
    
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")
    
    # Verify state (user_id)
    try:
        user_id = int(state)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid state")
    
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Exchange code for tokens
    if not settings.strava_client_id or not settings.strava_client_secret:
        raise HTTPException(status_code=500, detail="Strava not configured")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://www.strava.com/api/v3/oauth/token",
                data={
                    "client_id": settings.strava_client_id,
                    "client_secret": settings.strava_client_secret,
                    "code": code,
                    "grant_type": "authorization_code"
                }
            )
            response.raise_for_status()
            token_data = response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=400, detail=f"Failed to exchange token: {str(e)}")
    
    # Extract token data
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_at = token_data.get("expires_at")
    athlete = token_data.get("athlete", {})
    athlete_id = athlete.get("id")
    scope = token_data.get("scope", "")
    
    if not all([access_token, refresh_token, expires_at, athlete_id]):
        raise HTTPException(status_code=400, detail="Invalid token response from Strava")
    
    # Save or update Strava connection
    existing = db.query(StravaConnection).filter(
        StravaConnection.user_id == user_id
    ).first()
    
    if existing:
        existing.athlete_id = athlete_id
        existing.access_token = access_token
        existing.refresh_token = refresh_token
        existing.expires_at = expires_at
        existing.scope = scope
        existing.updated_at = datetime.utcnow()
    else:
        connection = StravaConnection(
            user_id=user_id,
            athlete_id=athlete_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            scope=scope
        )
        db.add(connection)
    
    db.commit()
    
    # Redirect to profile with success message
    return RedirectResponse(url="/static/templates/profile.html?strava_connected=true")


@router.get("/status")
async def get_strava_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if current user has connected their Strava account.
    """
    connection = db.query(StravaConnection).filter(
        StravaConnection.user_id == current_user.id
    ).first()
    
    if not connection:
        return {"connected": False}
    
    # Check if token is expired
    now_timestamp = int(datetime.utcnow().timestamp())
    is_expired = connection.expires_at < now_timestamp
    
    return {
        "connected": True,
        "athlete_id": connection.athlete_id,
        "expires_at": connection.expires_at,
        "is_expired": is_expired,
        "scope": connection.scope
    }


@router.delete("/disconnect")
async def disconnect_strava(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disconnect Strava account from user.
    """
    connection = db.query(StravaConnection).filter(
        StravaConnection.user_id == current_user.id
    ).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Strava not connected")
    
    # Optionally, you could revoke the token on Strava's side here
    # For now, just delete the local connection
    db.delete(connection)
    db.commit()
    
    return {"message": "Strava disconnected successfully"}


@router.post("/refresh-token")
async def refresh_access_token(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Refresh the Strava access token using the refresh token.
    This is useful when the access token expires (after 6 hours).
    """
    connection = db.query(StravaConnection).filter(
        StravaConnection.user_id == current_user.id
    ).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Strava not connected")
    
    if not settings.strava_client_id or not settings.strava_client_secret:
        raise HTTPException(status_code=500, detail="Strava not configured")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://www.strava.com/api/v3/oauth/token",
                data={
                    "client_id": settings.strava_client_id,
                    "client_secret": settings.strava_client_secret,
                    "refresh_token": connection.refresh_token,
                    "grant_type": "refresh_token"
                }
            )
            response.raise_for_status()
            token_data = response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=400, detail=f"Failed to refresh token: {str(e)}")
    
    # Update connection with new tokens
    connection.access_token = token_data.get("access_token")
    connection.refresh_token = token_data.get("refresh_token")
    connection.expires_at = token_data.get("expires_at")
    connection.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": "Token refreshed successfully",
        "expires_at": connection.expires_at
    }
