import json
from typing import Optional
from pywebpush import webpush, WebPushException

from app.core.config import settings
from app.models.push_subscription import PushSubscription


def send_push_notification(db, user_id: int, title: str, body: str, url: Optional[str] = None):
    """Send a push notification to all subscriptions of a user.
    Silently ignores errors per subscription.
    """
    if not settings.vapid_public_key or not settings.vapid_private_key:
        # Push is not configured
        return

    subs = db.query(PushSubscription).filter(PushSubscription.user_id == user_id).all()
    payload = {
        "title": title,
        "body": body,
    }
    if url:
        payload["url"] = url

    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=json.dumps(payload),
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_subject},
            )
        except WebPushException:
            # Remove invalid subscription
            db.delete(sub)
            db.commit()
        except Exception:
            # Ignore other errors to avoid breaking the flow
            continue
