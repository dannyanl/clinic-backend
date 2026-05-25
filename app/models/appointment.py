from enum import StrEnum

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.database.database import Base


class AppointmentStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"
    CHECKED_IN = "checked_in"


class AppointmentSeries(Base):
    __tablename__ = "appointment_series"

    id = Column(Integer, primary_key=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    weekday = Column(Integer, nullable=False)
    start_time = Column(String(8), nullable=False)
    occurrences = Column(Integer, nullable=False, default=1)
    starting_on = Column(Date, nullable=False)
    reason = Column(String(255))
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"))
    series_id = Column(Integer, ForeignKey("appointment_series.id"))
    starts_at = Column(DateTime(timezone=True), nullable=False, index=True)
    ends_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(32), nullable=False, default=AppointmentStatus.PENDING.value)
    reason = Column(String(255))
    notes = Column(Text)
    is_telemedicine = Column(Boolean, nullable=False, default=False)
    telemedicine_url = Column(String(500))
    reminder_sent_at = Column(DateTime(timezone=True))
    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    doctor = relationship("Doctor", back_populates="appointments")
    patient = relationship("Patient", back_populates="appointments")
    location = relationship("Location")
    medical_record = relationship("MedicalRecord", back_populates="appointment", uselist=False, cascade="all, delete-orphan")
    payment = relationship("Payment", back_populates="appointment", uselist=False)
    survey = relationship("SurveyResponse", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_appt_doctor_starts", "doctor_id", "starts_at"),
        Index("ix_appt_patient_starts", "patient_id", "starts_at"),
        Index("ix_appt_tenant_starts", "tenant_id", "starts_at"),
    )


class WaitingListEntry(Base):
    __tablename__ = "waiting_list"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    specialty_id = Column(Integer, ForeignKey("specialties.id"))
    desired_from = Column(Date)
    desired_to = Column(Date)
    notes = Column(String(255))
    status = Column(String(32), nullable=False, default="open")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
