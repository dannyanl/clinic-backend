from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, func

from app.database.database import Base


class ReminderPolicy(Base):
    __tablename__ = "reminder_policies"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, default="default")
    hours_before = Column(Integer, nullable=False, default=24)
    channels = Column(String(64), nullable=False, default="email")  # csv: email,sms,whatsapp
    enabled = Column(String(8), nullable=False, default="true")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class NoShowEvent(Base):
    __tablename__ = "no_show_events"

    id = Column(Integer, primary_key=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    fee_charged = Column(Numeric(10, 2), nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
