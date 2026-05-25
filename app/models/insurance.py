from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database.database import Base


class InsuranceProvider(Base):
    __tablename__ = "insurance_providers"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), unique=True, nullable=False)
    code = Column(String(40), unique=True)


class PatientInsurance(Base):
    __tablename__ = "patient_insurances"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    provider_id = Column(Integer, ForeignKey("insurance_providers.id"), nullable=False)
    membership_number = Column(String(80), nullable=False)
    plan = Column(String(80))

    patient = relationship("Patient", back_populates="insurances")
    provider = relationship("InsuranceProvider")
