from enum import StrEnum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database.database import Base


class NotificationType(StrEnum):
    EMAIL = "email"
    SMS = "sms"


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    type = Column(String(16), nullable=False)
    recipient = Column(String(255), nullable=False)
    subject = Column(String(255))
    body = Column(Text)
    status = Column(String(32), nullable=False, default="sent")
    error = Column(Text)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
