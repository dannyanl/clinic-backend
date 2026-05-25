from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.database.database import Base


class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id = Column(Integer, primary_key=True)
    code = Column(String(64), unique=True, nullable=False)  # e.g. appointment.reminder
    channel = Column(String(16), nullable=False, default="email")  # email|sms|whatsapp
    subject = Column(String(255))
    body = Column(Text, nullable=False)
    locale = Column(String(8), nullable=False, default="es")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
