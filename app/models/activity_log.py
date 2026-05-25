from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database.database import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    action = Column(String(120), nullable=False)
    entity = Column(String(80))
    entity_id = Column(Integer)
    metadata_json = Column(Text)
    ip = Column(String(64))
    user_agent = Column(String(255))
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
