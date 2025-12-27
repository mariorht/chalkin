"""
Strava OAuth router - Handle authorization and token exchange.
"""
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload
import httpx
import io

from app.core.config import settings
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.strava_connection import StravaConnection
from app.models.session import Session as ClimbingSession
from app.models.ascent import Ascent
from app.models.grade import Grade


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
    
    print(f"DEBUG: Exchanging token with redirect_uri: {settings.strava_redirect_uri}")
    
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
            print(f"DEBUG: Strava response status: {response.status_code}")
            print(f"DEBUG: Strava response body: {response.text}")
            
            if response.status_code != 200:
                error_body = response.text
                try:
                    error_json = response.json()
                    error_body = str(error_json)
                except:
                    pass
                raise HTTPException(
                    status_code=400, 
                    detail=f"Strava authentication failed: {error_body}"
                )
            
            token_data = response.json()
        except httpx.HTTPError as e:
            error_msg = f"Failed to exchange token: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f" | Response: {e.response.text}"
            print(f"ERROR: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
    
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


async def get_valid_token(user_id: int, db: Session) -> str:
    """
    Get a valid access token for the user, refreshing if necessary.
    """
    connection = db.query(StravaConnection).filter(
        StravaConnection.user_id == user_id
    ).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Strava not connected")
    
    # Check if token is expired (with 5 min buffer)
    now_timestamp = int(datetime.utcnow().timestamp())
    if connection.expires_at < (now_timestamp + 300):  # Refresh 5 min before expiry
        # Refresh token
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
                
                # Update connection
                connection.access_token = token_data.get("access_token")
                connection.refresh_token = token_data.get("refresh_token")
                connection.expires_at = token_data.get("expires_at")
                connection.updated_at = datetime.utcnow()
                db.commit()
            except httpx.HTTPError as e:
                raise HTTPException(status_code=400, detail=f"Failed to refresh token: {str(e)}")
    
    return connection.access_token


def generate_gpx_file(lat: float, lon: float, start_time: datetime, duration: int, activity_name: str, description: str) -> bytes:
    """
    Generate a simple GPX file with a single point (gym location).
    """
    # Calculate end time
    end_time = start_time + timedelta(seconds=duration)
    
    # Format times in ISO 8601
    start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_time_str = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    gpx_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Chalkin" xmlns="http://www.topografix.com/GPX/1/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
  <metadata>
    <name>{activity_name}</name>
    <desc>{description}</desc>
    <time>{start_time_str}</time>
  </metadata>
  <trk>
    <name>{activity_name}</name>
    <type>RockClimbing</type>
    <trkseg>
      <trkpt lat="{lat}" lon="{lon}">
        <time>{start_time_str}</time>
      </trkpt>
      <trkpt lat="{lat}" lon="{lon}">
        <time>{end_time_str}</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>'''
    
    return gpx_content.encode('utf-8')


@router.post("/upload-session/{session_id}")
async def upload_session_to_strava(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a climbing session to Strava as a Rock Climbing activity.
    """
    try:
        # Get the session with gym relationship loaded
        session = db.query(ClimbingSession).options(joinedload(ClimbingSession.gym)).filter(
            ClimbingSession.id == session_id,
            ClimbingSession.user_id == current_user.id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Check if already uploaded (we'll allow re-upload but warn user)
        # The frontend should handle the confirmation
        
        # Get valid access token
        access_token = await get_valid_token(current_user.id, db)
        
        # Get ascents for this session with grade relationship loaded
        ascents = db.query(Ascent).options(joinedload(Ascent.grade)).filter(
            Ascent.session_id == session_id
        ).all()
        
        # Build activity description with ascent summary
        try:
            ascent_summary = build_ascent_summary(ascents)
        except Exception as e:
            # If summary fails, continue without it
            ascent_summary = f"Total bloques: {len(ascents)}"
        
        # Calculate duration
        if session.started_at and session.ended_at:
            duration = int((session.ended_at - session.started_at).total_seconds())
        elif session.ended_at:
            # Use 1 hour if only end time exists
            duration = 3600
        else:
            duration = 3600  # Default 1 hour if no end time
        
        # Prepare activity data
        activity_name = session.title or "Sesión de escalada en boulder"
        activity_description = session.subtitle or ""
        if ascent_summary:
            activity_description += f"\n\n{ascent_summary}"
        
        # Format start date - use started_at or created_at as fallback
        start_datetime = session.started_at or session.created_at
        if not start_datetime:
            raise HTTPException(status_code=400, detail="Session has no valid date")
        
        # Format as ISO 8601 (Strava expects this format)
        start_date_local = start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Check if gym has coordinates to generate GPX
        if session.gym and session.gym.latitude and session.gym.longitude:
            # Generate GPX file and upload
            gpx_content = generate_gpx_file(
                lat=session.gym.latitude,
                lon=session.gym.longitude,
                start_time=start_datetime,
                duration=duration,
                activity_name=activity_name,
                description=activity_description
            )
            
            # Upload GPX to Strava
            async with httpx.AsyncClient() as client:
                try:
                    files = {
                        'file': ('activity.gpx', gpx_content, 'application/gpx+xml')
                    }
                    data = {
                        'data_type': 'gpx',
                        'name': activity_name,
                        'description': activity_description.strip(),
                        'activity_type': 'RockClimbing',
                        'private': 1  # Private activity
                    }
                    
                    response = await client.post(
                        "https://www.strava.com/api/v3/uploads",
                        headers={
                            "Authorization": f"Bearer {access_token}"
                        },
                        files=files,
                        data=data,
                        timeout=30.0
                    )
                    response.raise_for_status()
                    upload_result = response.json()
                except httpx.HTTPError as e:
                    error_detail = str(e)
                    if hasattr(e, 'response') and e.response is not None:
                        try:
                            error_detail = e.response.json()
                        except:
                            error_detail = e.response.text
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Failed to upload GPX to Strava: {error_detail}"
                    )
            
            # Get activity ID from upload (may need to poll for completion)
            activity_id = upload_result.get("activity_id")
            if not activity_id:
                # Upload is processing, use the upload ID temporarily
                activity_id = upload_result.get("id")
            
        else:
            # No coordinates, create activity without GPX
            activity_data = {
                "name": activity_name,
                "sport_type": "RockClimbing",
                "start_date_local": start_date_local,
                "elapsed_time": duration,
                "description": activity_description.strip(),
                "trainer": False,
                "commute": False,
                "hide_from_home": True
            }
            
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        "https://www.strava.com/api/v3/activities",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Content-Type": "application/json"
                        },
                        json=activity_data,
                        timeout=30.0
                    )
                    response.raise_for_status()
                    activity = response.json()
                    activity_id = activity.get("id")
                except httpx.HTTPError as e:
                    error_detail = str(e)
                    if hasattr(e, 'response') and e.response is not None:
                        try:
                            error_detail = e.response.json()
                        except:
                            error_detail = e.response.text
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Failed to upload to Strava: {error_detail}"
                    )
        
        # Save Strava activity ID
        session.strava_activity_id = activity_id
        db.commit()
        
        return {
            "message": "Activity uploaded to Strava successfully",
            "strava_activity_id": activity_id,
            "strava_url": f"https://www.strava.com/activities/{activity_id}"
        }
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log and return any unexpected errors
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error uploading to Strava: {error_trace}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal error while uploading to Strava: {str(e)}"
        )


def build_ascent_summary(ascents) -> str:
    """
    Build a formatted summary of ascents with emojis.
    """
    if not ascents:
        return ""
    
    # Group by status (handle both string and enum values)
    flash_count = 0
    send_count = 0
    repeat_count = 0
    project_count = 0
    
    for a in ascents:
        # Get status value - handle both enum and string
        status_value = a.status.value if hasattr(a.status, 'value') else str(a.status)
        status_lower = status_value.lower()
        
        if status_lower == "flash":
            flash_count += 1
        elif status_lower == "send":
            send_count += 1
        elif status_lower == "repeat":
            repeat_count += 1
        elif status_lower == "project":
            project_count += 1
    
    # Group by grade
    grade_counts = {}
    for ascent in ascents:
        try:
            if hasattr(ascent, 'grade') and ascent.grade is not None:
                # Get the label (not name) from grade
                grade_name = None
                
                if hasattr(ascent.grade, 'label'):
                    grade_name = ascent.grade.label
                elif hasattr(ascent.grade, '__dict__') and 'label' in ascent.grade.__dict__:
                    grade_name = ascent.grade.__dict__['label']
                
                if grade_name:
                    # Clean the grade name
                    grade_name = str(grade_name).strip()
                    if grade_name and not grade_name.startswith('<') and grade_name != 'None':
                        grade_counts[grade_name] = grade_counts.get(grade_name, 0) + 1
        except Exception as e:
            print(f"Error processing grade for ascent: {e}")
            continue
    
    # Color emoji mapping
    color_emojis = {
        'blanco': '⚪',
        'amarillo': '🟡',
        'naranja': '🟠',
        'verde': '🟢',
        'azul': '🔵',
        'rojo': '🔴',
        'negro': '⚫',
        'morado': '🟣',
        'violeta': '🟣',
        'rosa': '🩷',
        'marron': '🟤',
        'marrón': '🟤',
        'gris': '⚪',
    }
    
    summary_parts = []
    
    # Status summary
    status_parts = []
    if flash_count > 0:
        status_parts.append(f"⚡ {flash_count} flash")
    if send_count > 0:
        status_parts.append(f"✅ {send_count} encadenado{'s' if send_count > 1 else ''}")
    if repeat_count > 0:
        status_parts.append(f"🔄 {repeat_count} repetido{'s' if repeat_count > 1 else ''}")
    if project_count > 0:
        status_parts.append(f"🎯 {project_count} proyecto{'s' if project_count > 1 else ''}")
    
    if status_parts:
        summary_parts.append("📊 " + " | ".join(status_parts))
    
    # Grade summary (top 5 most common)
    if grade_counts:
        sorted_grades = sorted(grade_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        grade_parts = []
        for grade, count in sorted_grades:
            # Get emoji based on color name
            emoji = color_emojis.get(grade.lower(), '🔘')
            grade_parts.append(f"  {emoji} {grade}: {count}")
        grade_summary = "\n".join(grade_parts)
        summary_parts.append(f"\n🧗 Bloques:\n{grade_summary}")
    
    # Total count
    total = len(ascents)
    summary_parts.append(f"\n📈 Total: {total} bloque{'s' if total > 1 else ''}")
    
    return "\n".join(summary_parts)
