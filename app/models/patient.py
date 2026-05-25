from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    dni = Column(String(40))
    birth_date = Column(Date)
    blood_type = Column(String(8))
    allergies = Column(Text)
    notes = Column(Text)
    # E.164 international phone format e.g. +14155552671
    phone_e164 = Column(String(20))
    emergency_contact = Column(String(255))
    emergency_phone_e164 = Column(String(20))
    # ISO 3166-1 alpha-2 country code e.g. US, AR, MX, BR
    country_code = Column(String(2))
    preferred_lang = Column(String(8))
    deleted_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient")
    insurances = relationship("PatientInsurance", back_populates="patient", cascade="all, delete-orphan")
    medical_records = relationship("MedicalRecord", back_populates="patient")
