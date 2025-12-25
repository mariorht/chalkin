from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", "endpoint", name="uq_push_sub_user_endpoint"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    endpoint = Column(String(512), nullable=False)
    p256dh = Column(String(255), nullable=False)
    auth = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="push_subscriptions")
