from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database.database import Base


class SurveyResponse(Base):
    __tablename__ = "survey_responses"

    id = Column(Integer, primary_key=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id", ondelete="CASCADE"),
                            nullable=False, unique=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    nps_score = Column(Integer)  # 0-10
    comments = Column(Text)
    token = Column(String(128), unique=True, nullable=False, index=True)
    sent_at = Column(DateTime(timezone=True))
    answered_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
