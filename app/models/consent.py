from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database.database import Base


class ConsentTemplate(Base):
    __tablename__ = "consent_templates"

    id = Column(Integer, primary_key=True)
    code = Column(String(64), nullable=False, unique=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    active = Column(String(8), nullable=False, default="active")


class ConsentSignature(Base):
    __tablename__ = "consent_signatures"

    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey("consent_templates.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    signed_at = Column(DateTime, server_default=func.now(), nullable=False)
    signature_text = Column(String(255), nullable=False)
    ip = Column(String(64))
    user_agent = Column(String(255))
    snapshot = Column(Text, nullable=False)  # body snapshot at signing time
