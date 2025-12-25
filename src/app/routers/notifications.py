from typing import Optional
import json
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.base import get_db
from app.core.config import settings
from app.models.push_subscription import PushSubscription
from app.services.push import send_push_notification

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class SubscriptionPayload(BaseModel):
    endpoint: str
    p256dh: str = Field(..., description="User public key")
    auth: str = Field(..., description="Auth secret")


@router.get("/public-key")
def get_public_key():
    """Expose the VAPID public key to the client."""
    if not settings.vapid_public_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="VAPID key not configured")
    return {"public_key": settings.vapid_public_key}


@router.post("/subscribe")
def subscribe(
    payload: SubscriptionPayload,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Save or update a push subscription for the current user."""
    # Upsert subscription
    sub = db.query(PushSubscription).filter(
        PushSubscription.user_id == current_user.id,
        PushSubscription.endpoint == payload.endpoint
    ).first()

    if not sub:
        sub = PushSubscription(
            user_id=current_user.id,
            endpoint=payload.endpoint,
            p256dh=payload.p256dh,
            auth=payload.auth,
        )
        db.add(sub)
    else:
        sub.p256dh = payload.p256dh
        sub.auth = payload.auth

    db.commit()
    db.refresh(sub)
    return {"status": "subscribed"}


@router.delete("/subscribe")
def unsubscribe(
    endpoint: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    sub = db.query(PushSubscription).filter(
        PushSubscription.user_id == current_user.id,
        PushSubscription.endpoint == endpoint
    ).first()
    if sub:
        db.delete(sub)
        db.commit()
    return {"status": "unsubscribed"}


@router.post("/test")
def test_push(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Send a test notification to the current user."""
    if not settings.vapid_public_key or not settings.vapid_private_key:
        raise HTTPException(status_code=503, detail="VAPID keys not configured")

    send_push_notification(
        db=db,
        user_id=current_user.id,
        title="Notificación de prueba",
        body="Probando push en Chalkin",
        url="/friends",
    )
    return {"status": "sent"}
