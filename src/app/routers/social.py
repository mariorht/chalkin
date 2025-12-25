"""
Social router - friends, search, and activity feed.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.friendship import Friendship, FriendshipStatus
from app.services.push import send_push_notification
from app.models.session import Session as ClimbingSession
from app.models.ascent import Ascent, AscentStatus
from app.models.grade import Grade
from app.models.gym import Gym
from app.schemas.social import (
    UserSearchResult, 
    FriendshipCreate, 
    FriendshipResponse,
    FriendResponse,
    FeedItem,
    FeedResponse
)

router = APIRouter(prefix="/social", tags=["Social"])


@router.get("/search", response_model=List[UserSearchResult])
def search_users(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Search for users by username.
    Returns users matching the query with their friendship status.
    """
    # Search users (case insensitive)
    users = db.query(User).filter(
        User.username.ilike(f"%{q}%"),
        User.id != current_user.id
    ).limit(limit).all()
    
    results = []
    for user in users:
        # Check friendship status
        friendship = db.query(Friendship).filter(
            or_(
                and_(Friendship.user_id == current_user.id, Friendship.friend_id == user.id),
                and_(Friendship.user_id == user.id, Friendship.friend_id == current_user.id)
            )
        ).first()
        
        friendship_status = None
        if friendship:
            if friendship.status == FriendshipStatus.ACCEPTED:
                friendship_status = "accepted"
            elif friendship.status == FriendshipStatus.PENDING:
                if friendship.user_id == current_user.id:
                    friendship_status = "pending"  # I sent the request
                else:
                    friendship_status = "pending_received"  # They sent me a request
        
        results.append(UserSearchResult(
            id=user.id,
            username=user.username,
            profile_picture=user.profile_picture,
            friendship_status=friendship_status
        ))
    
    return results


@router.post("/friends", response_model=FriendshipResponse, status_code=status.HTTP_201_CREATED)
def send_friend_request(
    request: FriendshipCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send a friend request to another user.
    """
    if request.friend_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send friend request to yourself"
        )
    
    # Check if user exists
    friend = db.query(User).filter(User.id == request.friend_id).first()
    if not friend:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if friendship already exists (in either direction)
    existing = db.query(Friendship).filter(
        or_(
            and_(Friendship.user_id == current_user.id, Friendship.friend_id == request.friend_id),
            and_(Friendship.user_id == request.friend_id, Friendship.friend_id == current_user.id)
        )
    ).first()
    
    if existing:
        if existing.status == FriendshipStatus.ACCEPTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already friends"
            )
        elif existing.status == FriendshipStatus.PENDING:
            # If they sent us a request, accept it instead
            if existing.user_id == request.friend_id:
                existing.status = FriendshipStatus.ACCEPTED
                db.commit()
                db.refresh(existing)

                # Notify sender that request was accepted
                send_push_notification(
                    db=db,
                    user_id=existing.user_id,
                    title="Solicitud aceptada",
                    body=f"{current_user.username} aceptó tu solicitud",
                    url="/friends"
                )

                return FriendshipResponse(
                    id=existing.id,
                    user_id=existing.user_id,
                    friend_id=existing.friend_id,
                    status=existing.status.value,
                    created_at=existing.created_at,
                    user_username=friend.username,
                    friend_username=current_user.username
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Friend request already pending"
            )
    
    # Create new friend request
    friendship = Friendship(
        user_id=current_user.id,
        friend_id=request.friend_id,
        status=FriendshipStatus.PENDING
    )
    db.add(friendship)
    db.commit()
    db.refresh(friendship)

    # Notify the recipient about the new request
    send_push_notification(
        db=db,
        user_id=friend.id,
        title="Nueva solicitud de amistad",
        body=f"{current_user.username} quiere ser tu amigo",
        url="/friends"
    )
    
    return FriendshipResponse(
        id=friendship.id,
        user_id=friendship.user_id,
        friend_id=friendship.friend_id,
        status=friendship.status.value,
        created_at=friendship.created_at,
        user_username=current_user.username,
        friend_username=friend.username
    )


@router.get("/friends", response_model=List[FriendResponse])
def list_friends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all accepted friends.
    """
    friendships = db.query(Friendship).filter(
        or_(
            Friendship.user_id == current_user.id,
            Friendship.friend_id == current_user.id
        ),
        Friendship.status == FriendshipStatus.ACCEPTED
    ).all()
    
    friends = []
    for f in friendships:
        if f.user_id == current_user.id:
            friend_user = db.query(User).filter(User.id == f.friend_id).first()
        else:
            friend_user = db.query(User).filter(User.id == f.user_id).first()
        
        if friend_user:
            friends.append(FriendResponse(
                id=friend_user.id,
                username=friend_user.username,
                friendship_id=f.id,
                since=f.updated_at
            ))
    
    return friends


@router.get("/friends/requests", response_model=List[FriendshipResponse])
def list_friend_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List pending friend requests received.
    """
    requests = db.query(Friendship).filter(
        Friendship.friend_id == current_user.id,
        Friendship.status == FriendshipStatus.PENDING
    ).all()
    
    results = []
    for r in requests:
        sender = db.query(User).filter(User.id == r.user_id).first()
        results.append(FriendshipResponse(
            id=r.id,
            user_id=r.user_id,
            friend_id=r.friend_id,
            status=r.status.value,
            created_at=r.created_at,
            user_username=sender.username if sender else None,
            friend_username=current_user.username
        ))
    
    return results


@router.post("/friends/requests/{request_id}/accept", response_model=FriendshipResponse)
def accept_friend_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Accept a friend request.
    """
    friendship = db.query(Friendship).filter(
        Friendship.id == request_id,
        Friendship.friend_id == current_user.id,
        Friendship.status == FriendshipStatus.PENDING
    ).first()
    
    if not friendship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friend request not found"
        )
    
    friendship.status = FriendshipStatus.ACCEPTED
    db.commit()
    db.refresh(friendship)
    
    sender = db.query(User).filter(User.id == friendship.user_id).first()

    # Notify sender that request was accepted
    if sender:
        send_push_notification(
            db=db,
            user_id=sender.id,
            title="Solicitud aceptada",
            body=f"{current_user.username} aceptó tu solicitud",
            url="/friends"
        )
    
    return FriendshipResponse(
        id=friendship.id,
        user_id=friendship.user_id,
        friend_id=friendship.friend_id,
        status=friendship.status.value,
        created_at=friendship.created_at,
        user_username=sender.username if sender else None,
        friend_username=current_user.username
    )


@router.post("/friends/requests/{request_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
def reject_friend_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reject a friend request.
    """
    friendship = db.query(Friendship).filter(
        Friendship.id == request_id,
        Friendship.friend_id == current_user.id,
        Friendship.status == FriendshipStatus.PENDING
    ).first()
    
    if not friendship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friend request not found"
        )
    
    db.delete(friendship)
    db.commit()


@router.delete("/friends/{friend_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_friend(
    friend_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove a friend.
    """
    friendship = db.query(Friendship).filter(
        or_(
            and_(Friendship.user_id == current_user.id, Friendship.friend_id == friend_id),
            and_(Friendship.user_id == friend_id, Friendship.friend_id == current_user.id)
        ),
        Friendship.status == FriendshipStatus.ACCEPTED
    ).first()
    
    if not friendship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friendship not found"
        )
    
    db.delete(friendship)
    db.commit()


@router.get("/feed", response_model=FeedResponse)
def get_activity_feed(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get activity feed with own sessions and friends' sessions.
    Ordered by date, most recent first.
    """
    # Get list of friend IDs
    friendships = db.query(Friendship).filter(
        or_(
            Friendship.user_id == current_user.id,
            Friendship.friend_id == current_user.id
        ),
        Friendship.status == FriendshipStatus.ACCEPTED
    ).all()
    
    friend_ids = set()
    for f in friendships:
        if f.user_id == current_user.id:
            friend_ids.add(f.friend_id)
        else:
            friend_ids.add(f.user_id)
    
    # Include current user
    user_ids = list(friend_ids) + [current_user.id]
    
    # Get sessions from all these users
    sessions = db.query(ClimbingSession).filter(
        ClimbingSession.user_id.in_(user_ids)
    ).order_by(desc(ClimbingSession.date), desc(ClimbingSession.started_at)).offset(skip).limit(limit + 1).all()
    
    has_more = len(sessions) > limit
    sessions = sessions[:limit]
    
    # Build feed items
    items = []
    for session in sessions:
        # Get user info
        user = db.query(User).filter(User.id == session.user_id).first()
        
        # Get gym info
        gym = db.query(Gym).filter(Gym.id == session.gym_id).first()
        
        # Get ascents stats
        ascents = db.query(Ascent).filter(Ascent.session_id == session.id).all()
        total_ascents = len(ascents)
        flashes = len([a for a in ascents if a.status == AscentStatus.FLASH])
        sends = len([a for a in ascents if a.status in [AscentStatus.SEND, AscentStatus.FLASH]])
        
        # Get max grade
        max_grade_label = None
        if ascents:
            send_ascents = [a for a in ascents if a.status != AscentStatus.PROJECT]
            if send_ascents:
                grade_ids = [a.grade_id for a in send_ascents]
                max_grade = db.query(Grade).filter(
                    Grade.id.in_(grade_ids)
                ).order_by(desc(Grade.relative_difficulty)).first()
                if max_grade:
                    max_grade_label = max_grade.label
        
        items.append(FeedItem(
            session_id=session.id,
            user_id=session.user_id,
            username=user.username if user else "Usuario",
            profile_picture=user.profile_picture if user else None,
            gym_id=session.gym_id,
            gym_name=gym.name if gym else "Gimnasio",
            gym_location=gym.location if gym else None,
            title=session.title,
            subtitle=session.subtitle,
            date=session.date,
            started_at=session.started_at,
            ended_at=session.ended_at,
            total_ascents=total_ascents,
            flashes=flashes,
            sends=sends,
            max_grade_label=max_grade_label,
            is_own=session.user_id == current_user.id
        ))
    
    return FeedResponse(items=items, has_more=has_more)
