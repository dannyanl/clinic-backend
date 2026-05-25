from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.database.database import Base


class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id", ondelete="SET NULL"), unique=True)
    chief_complaint = Column(String(255))
    diagnosis = Column(Text)
    # ICD-10 / ICD-11 international disease classification codes
    icd10_code = Column(String(16))
    icd11_code = Column(String(16))
    treatment_plan = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    patient = relationship("Patient", back_populates="medical_records")
    doctor = relationship("Doctor")
    appointment = relationship("Appointment", back_populates="medical_record")
    prescriptions = relationship("Prescription", back_populates="record", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="record", cascade="all, delete-orphan")


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, ForeignKey("medical_records.id", ondelete="CASCADE"), nullable=False)
    drug = Column(String(255), nullable=False)
    dosage = Column(String(120))
    frequency = Column(String(120))
    duration = Column(String(120))
    instructions = Column(Text)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    record = relationship("MedicalRecord", back_populates="prescriptions")


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, ForeignKey("medical_records.id", ondelete="CASCADE"))
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(120))
    size_bytes = Column(Integer)
    storage_path = Column(String(500), nullable=False)
    uploaded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    record = relationship("MedicalRecord", back_populates="attachments")
