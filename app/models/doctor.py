from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.database.database import Base


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    specialty_id = Column(Integer, ForeignKey("specialties.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"))
    license_number = Column(String(80), nullable=False)
    # Country where the license was issued (ISO 3166-1 alpha-2)
    license_country = Column(String(2))
    bio = Column(Text)
    consultation_fee = Column(Numeric(10, 2), nullable=False, default=0)
    consultation_currency = Column(String(8), nullable=False, server_default="USD")

    user = relationship("User", back_populates="doctor")
    specialty = relationship("Specialty", back_populates="doctors")
    location = relationship("Location")
    schedules = relationship("Schedule", back_populates="doctor", cascade="all, delete-orphan")
    absences = relationship("Absence", back_populates="doctor", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="doctor")
