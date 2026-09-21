"""
Strava OAuth router - Handle authorization and token exchange.
"""
from typing import Optional
from datetime import datetime, timedelta
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload
import httpx
import io
import logging
import xml.etree.ElementTree as ET
import re
import math

from app.core.config import settings
from app.core.deps import get_db, get_current_user
from app.core.security import create_oauth_state, decrypt_token, encrypt_token, verify_oauth_state
from app.models.user import User
from app.models.strava_connection import StravaConnection
from app.models.session import Session as ClimbingSession
from app.models.ascent import Ascent
from app.models.grade import Grade
from app.models.session_exercise import SessionExercise
from app.utils.svg_parser import (
    extract_svg_paths,
    svg_to_points,
    scale_and_center_points,
)
import os


router = APIRouter(prefix="/strava", tags=["strava"])
logger = logging.getLogger(__name__)


@router.get("/connect")
async def connect_strava(current_user: User = Depends(get_current_user)):
    """
    Initiate Strava OAuth flow.
    Returns the authorization URL for the frontend to redirect.
    """
    if not settings.strava_client_id or not settings.strava_redirect_uri:
        raise HTTPException(status_code=500, detail="Strava not configured")
    
    # Build authorization URL with a signed, expiring state (CSRF protection)
    state = quote(create_oauth_state(current_user.id))
    auth_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={settings.strava_client_id}"
        f"&response_type=code"
        f"&redirect_uri={settings.strava_redirect_uri}"
        f"&approval_prompt=auto"
        f"&scope=activity:write,read"
        f"&state={state}"
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
    
    # Verify the signed state and recover the user id
    user_id = verify_oauth_state(state)
    if user_id is None:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Exchange code for tokens
    if not settings.strava_client_id or not settings.strava_client_secret:
        raise HTTPException(status_code=500, detail="Strava not configured")
    
    # Increase timeout for IPv6-only servers
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                "https://www.strava.com/api/v3/oauth/token",
                data={
                    "client_id": settings.strava_client_id,
                    "client_secret": settings.strava_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.strava_redirect_uri
                }
            )
            
            if response.status_code != 200:
                # Do not forward Strava's response body to the client
                logger.warning(
                    "Strava token exchange failed with status %s",
                    response.status_code,
                )
                raise HTTPException(
                    status_code=400,
                    detail="Strava authentication failed"
                )
            
            token_data = response.json()
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("Strava token exchange error: %s", e)
            raise HTTPException(status_code=400, detail="Strava authentication failed")
    
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
        existing.access_token = encrypt_token(access_token)
        existing.refresh_token = encrypt_token(refresh_token)
        existing.expires_at = expires_at
        existing.scope = scope
        existing.updated_at = datetime.utcnow()
    else:
        connection = StravaConnection(
            user_id=user_id,
            athlete_id=athlete_id,
            access_token=encrypt_token(access_token),
            refresh_token=encrypt_token(refresh_token),
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
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                "https://www.strava.com/api/v3/oauth/token",
                data={
                    "client_id": settings.strava_client_id,
                    "client_secret": settings.strava_client_secret,
                    "refresh_token": decrypt_token(connection.refresh_token),
                    "grant_type": "refresh_token"
                }
            )
            response.raise_for_status()
            token_data = response.json()
        except httpx.HTTPError as e:
            logger.warning("Failed to refresh Strava token: %s", e)
            raise HTTPException(status_code=400, detail="Failed to refresh token")
    
    # Update connection with new tokens
    connection.access_token = encrypt_token(token_data.get("access_token"))
    connection.refresh_token = encrypt_token(token_data.get("refresh_token"))
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
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    "https://www.strava.com/api/v3/oauth/token",
                    data={
                        "client_id": settings.strava_client_id,
                        "client_secret": settings.strava_client_secret,
                        "refresh_token": decrypt_token(connection.refresh_token),
                        "grant_type": "refresh_token"
                    }
                )
                response.raise_for_status()
                token_data = response.json()
                
                # Update connection
                connection.access_token = encrypt_token(token_data.get("access_token"))
                connection.refresh_token = encrypt_token(token_data.get("refresh_token"))
                connection.expires_at = token_data.get("expires_at")
                connection.updated_at = datetime.utcnow()
                db.commit()
            except httpx.HTTPError as e:
                logger.warning("Failed to refresh Strava token: %s", e)
                raise HTTPException(status_code=400, detail="Failed to refresh token")
    
    return decrypt_token(connection.access_token)


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
        
        # Check if already uploaded
        if session.strava_activity_id:
            # Return info about existing upload instead of creating duplicate
            return {
                "message": "Session already uploaded to Strava",
                "strava_activity_id": session.strava_activity_id,
                "strava_url": f"https://www.strava.com/activities/{session.strava_activity_id}",
                "already_uploaded": True
            }
        
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
        
        # Get exercises for this session
        exercises_summary = ""
        try:
            exercises = db.query(SessionExercise).filter(
                SessionExercise.session_id == session_id
            ).all()
            
            # Build exercises summary
            if exercises:
                exercise_lines = []
                for ex in exercises:
                    type_name = {
                        'pullups': 'Dominadas',
                        'campus': 'Campus',
                        'fingerboard': 'Fingerboard'
                    }.get(ex.exercise_type, ex.exercise_type.capitalize())
                    
                    details = []
                    if ex.sets:
                        details.append(f"{ex.sets}x")
                    if ex.reps:
                        details.append(f"{ex.reps}")
                    if ex.weight:
                        details.append(f"{ex.weight}kg")
                    
                    line = f"- {type_name}"
                    if details:
                        line += f": {' '.join(details)}"
                    if ex.notes:
                        line += f" ({ex.notes})"
                    exercise_lines.append(line)
                
                exercises_summary = "\n\nEntrenamiento complementario:\n" + "\n".join(exercise_lines)
        except Exception as e:
            # Continue without exercises summary
            pass
        
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
        if exercises_summary:
            activity_description += exercises_summary
        
        # Add Chalkin branding
        activity_description += "\n\nActividad registrada con Chalkin"
        
        # Format start date - use started_at or created_at as fallback
        start_datetime = session.started_at or session.created_at
        if not start_datetime:
            raise HTTPException(status_code=400, detail="Session has no valid date")
        
        # Format as ISO 8601 (Strava expects this format)
        start_date_local = start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Check if gym has coordinates to generate GPX
        if session.gym and session.gym.latitude and session.gym.longitude:
            # Generate GPX file with logo shape
            try:
                # Try to load the simplified logo SVG
                svg_path = "app/static/icons/logoChalkin_invertido_simple.svg"
                if not os.path.exists(svg_path):
                    raise Exception(f"Logo SVG not found at {svg_path}")
                
                paths = extract_svg_paths(svg_path)
                if not paths:
                    raise Exception("No paths found in SVG")
                
                # Convert all paths to points
                all_points = []
                for path_d in paths:
                    try:
                        points = svg_to_points(path_d, num_points=300)
                        if points:
                            all_points.extend(points)
                    except:
                        pass
                
                if not all_points:
                    raise Exception("No points generated from SVG")
                
                # Scale and center around gym location
                gps_points = scale_and_center_points(
                    all_points,
                    session.gym.latitude,
                    session.gym.longitude,
                    scale_meters=50  # 50 meter logo
                )
                gpx_content = generate_gpx_from_points(
                    gps_points,
                    start_datetime,
                    duration,
                    activity_name,
                    activity_description
                ).encode('utf-8')
            except Exception as e:
                # If logo generation fails, use simple single point
                logger.warning("Failed to generate logo GPX, using simple point: %s", e)
                gpx_content = generate_gpx_file(
                    lat=session.gym.latitude,
                    lon=session.gym.longitude,
                    start_time=start_datetime,
                    duration=duration,
                    activity_name=activity_name,
                    description=activity_description
                )
            
            # Upload GPX to Strava
            async with httpx.AsyncClient(timeout=30.0) as client:
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
                    logger.warning("Failed to upload GPX to Strava: %s", e)
                    raise HTTPException(
                        status_code=400,
                        detail="Failed to upload activity to Strava"
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
            
            async with httpx.AsyncClient(timeout=30.0) as client:
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
                    logger.warning("Failed to upload activity to Strava: %s", e)
                    raise HTTPException(
                        status_code=400,
                        detail="Failed to upload activity to Strava"
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
        # Log the details server-side but do not leak them to the client
        logger.exception("Unexpected error uploading to Strava")
        raise HTTPException(
            status_code=500,
            detail="Internal error while uploading to Strava"
        )


def build_ascent_summary(ascents) -> str:
    """
    Build a formatted summary of ascents with emojis.
    """
    if not ascents:
        return ""
    
    # Filter out projects - only count completed ascents
    completed_ascents = []
    for a in ascents:
        status_value = a.status.value if hasattr(a.status, 'value') else str(a.status)
        status_lower = status_value.lower()
        if status_lower != "project":  # Exclude projects
            completed_ascents.append(a)
    
    # Group by status (handle both string and enum values)
    flash_count = 0
    send_count = 0
    repeat_count = 0
    
    for a in completed_ascents:
        # Get status value - handle both enum and string
        status_value = a.status.value if hasattr(a.status, 'value') else str(a.status)
        status_lower = status_value.lower()
        
        if status_lower == "flash":
            flash_count += 1
        elif status_lower == "send":
            send_count += 1
        elif status_lower == "repeat":
            repeat_count += 1
    
    # Group by grade (only completed ascents)
    grade_counts = {}
    for ascent in completed_ascents:
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
            logger.warning("Error processing grade for ascent: %s", e)
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
    
    # Status summary (without projects)
    status_parts = []
    if flash_count > 0:
        status_parts.append(f"⚡ {flash_count} flash")
    if send_count > 0:
        status_parts.append(f"✅ {send_count} encadenado{'s' if send_count > 1 else ''}")
    if repeat_count > 0:
        status_parts.append(f"🔄 {repeat_count} repetido{'s' if repeat_count > 1 else ''}")
    
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
    
    # Total count (only completed)
    total = len(completed_ascents)
    summary_parts.append(f"\n📈 Total: {total} bloque{'s' if total > 1 else ''}")
    
    return "\n".join(summary_parts)


def generate_gpx_from_points(points, start_time: datetime, duration: int, activity_name: str, description: str) -> str:
    """
    Generate GPX file from a list of (lat, lon) points.
    
    Args:
        points: List of (lat, lon) tuples
        start_time: Activity start time
        duration: Total duration in seconds
        activity_name: Name of the activity
        description: Activity description
    
    Returns:
        GPX XML string
    """
    if not points:
        # Return single point GPX as fallback
        return generate_gpx_file(0, 0, start_time, duration, activity_name, description)
    
    # Calculate time per point
    time_per_point = duration / len(points) if len(points) > 1 else duration
    
    # Build GPX XML
    gpx_header = f'''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Chalkin" xmlns="http://www.topografix.com/GPX/1/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
  <metadata>
    <name>{activity_name}</name>
    <desc>{description}</desc>
    <time>{start_time.strftime("%Y-%m-%dT%H:%M:%SZ")}</time>
  </metadata>
  <trk>
    <name>{activity_name}</name>
    <type>RockClimbing</type>
    <trkseg>
'''
    
    track_points = []
    for i, (lat, lon) in enumerate(points):
        point_time = start_time + timedelta(seconds=i * time_per_point)
        time_str = point_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        track_points.append(f'      <trkpt lat="{lat}" lon="{lon}">\n        <time>{time_str}</time>\n      </trkpt>')
    
    gpx_footer = '''
    </trkseg>
  </trk>
</gpx>'''
    
    return gpx_header + '\n'.join(track_points) + gpx_footer

