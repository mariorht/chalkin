"""
Stats router - user statistics and analytics (the Strava-like magic).
"""
from typing import List
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.session import Session as ClimbingSession
from app.models.ascent import Ascent, AscentStatus
from app.models.grade import Grade
from app.models.gym import Gym
from app.schemas.stats import UserStats, GradeDistribution, WeeklyStats, GymStats

router = APIRouter(prefix="/stats", tags=["Statistics"])


@router.get("/me", response_model=UserStats)
def get_my_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive statistics for the current user.
    This is the main stats endpoint - like Strava's dashboard.
    """
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Get all user's sessions
    sessions = db.query(ClimbingSession).filter(
        ClimbingSession.user_id == current_user.id
    ).all()
    
    session_ids = [s.id for s in sessions]
    
    # Get all ascents
    ascents = db.query(Ascent).filter(
        Ascent.session_id.in_(session_ids)
    ).all() if session_ids else []
    
    # Basic counts
    total_sessions = len(sessions)
    total_ascents = len(ascents)
    total_sends = len([a for a in ascents if a.status in [AscentStatus.SEND, AscentStatus.REPEAT, AscentStatus.FLASH]])
    total_flashes = len([a for a in ascents if a.status == AscentStatus.FLASH])
    
    # Time-based filtering
    sessions_this_week = len([s for s in sessions if s.date >= week_ago])
    sessions_this_month = len([s for s in sessions if s.date >= month_ago])
    
    week_session_ids = [s.id for s in sessions if s.date >= week_ago]
    month_session_ids = [s.id for s in sessions if s.date >= month_ago]
    
    ascents_this_week = [a for a in ascents if a.session_id in week_session_ids]
    ascents_this_month = len([a for a in ascents if a.session_id in month_session_ids])
    
    # Sends and flashes this week
    sends_this_week = len([a for a in ascents_this_week if a.status in [AscentStatus.SEND, AscentStatus.REPEAT, AscentStatus.FLASH]])
    flashes_this_week = len([a for a in ascents_this_week if a.status == AscentStatus.FLASH])
    ascents_this_week_count = len(ascents_this_week)
    
    # Max grade calculations
    max_grade_ever = None
    max_relative_difficulty = None
    current_max_grade = None
    
    if ascents:
        # Get max difficulty ever (only sends)
        send_ascents = [a for a in ascents if a.status in [AscentStatus.SEND, AscentStatus.REPEAT, AscentStatus.FLASH]]
        if send_ascents:
            grade_ids = [a.grade_id for a in send_ascents]
            max_grade = db.query(Grade).filter(
                Grade.id.in_(grade_ids)
            ).order_by(desc(Grade.relative_difficulty)).first()
            
            if max_grade:
                max_grade_ever = max_grade.label
                max_relative_difficulty = max_grade.relative_difficulty
        
        # Current max (last 30 days)
        recent_send_ascents = [a for a in send_ascents if a.session_id in month_session_ids]
        if recent_send_ascents:
            grade_ids = [a.grade_id for a in recent_send_ascents]
            current_max = db.query(Grade).filter(
                Grade.id.in_(grade_ids)
            ).order_by(desc(Grade.relative_difficulty)).first()
            
            if current_max:
                current_max_grade = current_max.label
    
    # Grade distribution
    grade_distribution = []
    if ascents:
        grade_counts = {}
        for ascent in ascents:
            gid = ascent.grade_id
            if gid not in grade_counts:
                grade_counts[gid] = {"count": 0, "sends": 0, "flashes": 0}
            grade_counts[gid]["count"] += 1
            if ascent.status in [AscentStatus.SEND, AscentStatus.REPEAT, AscentStatus.FLASH]:
                grade_counts[gid]["sends"] += 1
            if ascent.status == AscentStatus.FLASH:
                grade_counts[gid]["flashes"] += 1
        
        for grade_id, counts in grade_counts.items():
            grade = db.query(Grade).filter(Grade.id == grade_id).first()
            if grade:
                grade_distribution.append(GradeDistribution(
                    grade_label=grade.label,
                    color_hex=grade.color_hex,
                    relative_difficulty=grade.relative_difficulty,
                    count=counts["count"],
                    sends=counts["sends"],
                    flashes=counts["flashes"]
                ))
        
        # Sort by difficulty
        grade_distribution.sort(key=lambda x: x.relative_difficulty)
    
    # Gym breakdown
    gym_breakdown = []
    gym_session_counts = {}
    gym_ascent_counts = {}
    
    for session in sessions:
        gid = session.gym_id
        gym_session_counts[gid] = gym_session_counts.get(gid, 0) + 1
        session_ascents = [a for a in ascents if a.session_id == session.id]
        gym_ascent_counts[gid] = gym_ascent_counts.get(gid, 0) + len(session_ascents)
    
    for gym_id in gym_session_counts:
        gym = db.query(Gym).filter(Gym.id == gym_id).first()
        if gym:
            gym_breakdown.append(GymStats(
                gym_id=gym_id,
                gym_name=gym.name,
                total_sessions=gym_session_counts[gym_id],
                total_ascents=gym_ascent_counts.get(gym_id, 0)
            ))
    
    # Sort by sessions
    gym_breakdown.sort(key=lambda x: x.total_sessions, reverse=True)
    
    # Weekly progress (last 8 weeks)
    weekly_progress = []
    for i in range(8):
        week_end = today - timedelta(days=i * 7)
        week_start = week_end - timedelta(days=6)
        
        week_sessions = [s for s in sessions if week_start <= s.date <= week_end]
        week_session_ids = [s.id for s in week_sessions]
        week_ascents = [a for a in ascents if a.session_id in week_session_ids]
        
        week_sends = [a for a in week_ascents if a.status in [AscentStatus.SEND, AscentStatus.REPEAT, AscentStatus.FLASH]]
        week_flashes = [a for a in week_ascents if a.status == AscentStatus.FLASH]
        
        max_sent = None
        max_diff = None
        if week_sends:
            grade_ids = [a.grade_id for a in week_sends]
            max_g = db.query(Grade).filter(Grade.id.in_(grade_ids)).order_by(desc(Grade.relative_difficulty)).first()
            if max_g:
                max_sent = max_g.label
                max_diff = max_g.relative_difficulty
        
        weekly_progress.append(WeeklyStats(
            week_start=week_start,
            week_end=week_end,
            total_sessions=len(week_sessions),
            total_ascents=len(week_ascents),
            total_sends=len(week_sends),
            total_flashes=len(week_flashes),
            max_grade_sent=max_sent,
            max_relative_difficulty=max_diff
        ))
    
    # Reverse to show oldest first
    weekly_progress.reverse()
    
    return UserStats(
        total_sessions=total_sessions,
        total_ascents=total_ascents,
        total_sends=total_sends,
        total_flashes=total_flashes,
        max_grade_ever=max_grade_ever,
        max_relative_difficulty=max_relative_difficulty,
        current_max_grade=current_max_grade,
        max_grade_label=max_grade_ever,  # Alias for frontend
        message=_generate_motivational_message(sessions_this_week, sends_this_week, flashes_this_week),
        sessions_this_week=sessions_this_week,
        sessions_this_month=sessions_this_month,
        ascents_this_week=ascents_this_week_count,
        ascents_this_month=ascents_this_month,
        sends_this_week=sends_this_week,
        flashes_this_week=flashes_this_week,
        grade_distribution=grade_distribution,
        weekly_progress=weekly_progress,
        gym_breakdown=gym_breakdown
    )


@router.get("/summary")
def get_quick_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a quick summary for the dashboard.
    Lighter than the full stats endpoint.
    """
    today = date.today()
    week_ago = today - timedelta(days=7)
    
    # This week's sessions
    sessions = db.query(ClimbingSession).filter(
        ClimbingSession.user_id == current_user.id,
        ClimbingSession.date >= week_ago
    ).all()
    
    session_ids = [s.id for s in sessions]
    
    # Ascents this week
    ascents = db.query(Ascent).filter(
        Ascent.session_id.in_(session_ids)
    ).all() if session_ids else []
    
    sends = [a for a in ascents if a.status in [AscentStatus.SEND, AscentStatus.REPEAT, AscentStatus.FLASH]]
    flashes = [a for a in ascents if a.status == AscentStatus.FLASH]
    
    # Max grade this week
    max_grade = None
    if sends:
        grade_ids = [a.grade_id for a in sends]
        max_g = db.query(Grade).filter(Grade.id.in_(grade_ids)).order_by(desc(Grade.relative_difficulty)).first()
        if max_g:
            max_grade = max_g.label
    
    return {
        "sessions_this_week": len(sessions),
        "ascents_this_week": len(ascents),
        "sends_this_week": len(sends),
        "flashes_this_week": len(flashes),
        "max_grade_this_week": max_grade,
        "message": _generate_motivational_message(len(sessions), len(sends), len(flashes))
    }


def _generate_motivational_message(sessions: int, sends: int, flashes: int) -> str:
    """Generate a fun motivational message based on activity."""
    if sessions == 0:
        return "¡Es hora de volver al rocódromo! 🧗"
    elif sends == 0:
        return f"🧗 ¡{sessions} sesión{'es' if sessions > 1 else ''} esta semana! Añade tus bloques para trackear tu progreso."
    elif flashes >= 3:
        return f"🔥 ¡{flashes} flashes esta semana! ¡Estás que ardes!"
    elif sends >= 10:
        return f"💪 ¡{sends} bloques completados! ¡Vas a tope para la Superliga!"
    elif flashes >= 1:
        return f"⚡ ¡{sends} bloques y {flashes} flash{'es' if flashes > 1 else ''}! ¡Sigue así!"
    elif sessions >= 3:
        return "🎯 ¡Gran consistencia! El volumen es la clave."
    else:
        return f"👍 ¡Buen trabajo! {sends} bloque{'s' if sends != 1 else ''} encadenado{'s' if sends != 1 else ''} esta semana."


@router.get("/yearly")
def get_yearly_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get statistics for the last year.
    """
    today = date.today()
    year_ago = today - timedelta(days=365)
    
    # Get sessions from last year
    sessions = db.query(ClimbingSession).filter(
        ClimbingSession.user_id == current_user.id,
        ClimbingSession.date >= year_ago
    ).all()
    
    session_ids = [s.id for s in sessions]
    
    # Get all ascents from those sessions
    ascents = db.query(Ascent).filter(
        Ascent.session_id.in_(session_ids)
    ).all() if session_ids else []
    
    sends = [a for a in ascents if a.status in [AscentStatus.SEND, AscentStatus.REPEAT, AscentStatus.FLASH]]
    flashes = [a for a in ascents if a.status == AscentStatus.FLASH]
    
    # Max grade this year
    max_grade = None
    max_difficulty = None
    if sends:
        grade_ids = [a.grade_id for a in sends]
        max_g = db.query(Grade).filter(Grade.id.in_(grade_ids)).order_by(desc(Grade.relative_difficulty)).first()
        if max_g:
            max_grade = max_g.label
            max_difficulty = max_g.relative_difficulty
    
    # Monthly breakdown
    monthly_stats = []
    for i in range(12):
        month_end = today - timedelta(days=i * 30)
        month_start = month_end - timedelta(days=29)
        
        month_sessions = [s for s in sessions if month_start <= s.date <= month_end]
        month_session_ids = [s.id for s in month_sessions]
        month_ascents = [a for a in ascents if a.session_id in month_session_ids]
        month_sends = [a for a in month_ascents if a.status in [AscentStatus.SEND, AscentStatus.REPEAT, AscentStatus.FLASH]]
        month_flashes = [a for a in month_ascents if a.status == AscentStatus.FLASH]
        
        monthly_stats.append({
            "month": month_start.strftime("%b"),
            "sessions": len(month_sessions),
            "ascents": len(month_ascents),
            "sends": len(month_sends),
            "flashes": len(month_flashes)
        })
    
    monthly_stats.reverse()
    
    return {
        "total_sessions": len(sessions),
        "total_ascents": len(ascents),
        "total_sends": len(sends),
        "total_flashes": len(flashes),
        "max_grade": max_grade,
        "max_difficulty": max_difficulty,
        "monthly_stats": monthly_stats
    }


@router.get("/friends-comparison")
def get_friends_comparison(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Compare stats with friends.
    """
    from app.models.friendship import Friendship, FriendshipStatus
    from sqlalchemy import or_, and_
    
    today = date.today()
    month_ago = today - timedelta(days=30)
    
    # Get friends
    friendships = db.query(Friendship).filter(
        or_(
            and_(Friendship.user_id == current_user.id, Friendship.status == FriendshipStatus.ACCEPTED),
            and_(Friendship.friend_id == current_user.id, Friendship.status == FriendshipStatus.ACCEPTED)
        )
    ).all()
    
    friend_ids = []
    for f in friendships:
        if f.user_id == current_user.id:
            friend_ids.append(f.friend_id)
        else:
            friend_ids.append(f.user_id)
    
    # Include current user
    all_user_ids = [current_user.id] + friend_ids
    
    # Get stats for all users
    comparison = []
    for user_id in all_user_ids:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            continue
        
        # Get sessions this month
        sessions = db.query(ClimbingSession).filter(
            ClimbingSession.user_id == user_id,
            ClimbingSession.date >= month_ago
        ).all()
        
        session_ids = [s.id for s in sessions]
        
        ascents = db.query(Ascent).filter(
            Ascent.session_id.in_(session_ids)
        ).all() if session_ids else []
        
        sends = [a for a in ascents if a.status in [AscentStatus.SEND, AscentStatus.REPEAT, AscentStatus.FLASH]]
        flashes = [a for a in ascents if a.status == AscentStatus.FLASH]
        
        # Max grade
        max_grade = None
        max_difficulty = 0
        if sends:
            grade_ids = [a.grade_id for a in sends]
            max_g = db.query(Grade).filter(Grade.id.in_(grade_ids)).order_by(desc(Grade.relative_difficulty)).first()
            if max_g:
                max_grade = max_g.label
                max_difficulty = max_g.relative_difficulty
        
        comparison.append({
            "user_id": user_id,
            "username": user.username,
            "is_current_user": user_id == current_user.id,
            "sessions": len(sessions),
            "ascents": len(ascents),
            "sends": len(sends),
            "flashes": len(flashes),
            "max_grade": max_grade,
            "max_difficulty": max_difficulty
        })
    
    # Sort by sends (descending)
    comparison.sort(key=lambda x: (x["sends"], x["flashes"]), reverse=True)
    
    # Add rank
    for i, entry in enumerate(comparison):
        entry["rank"] = i + 1
    
    return {
        "period": "Último mes",
        "comparison": comparison
    }

