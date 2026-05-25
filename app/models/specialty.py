from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.database import Base


class Specialty(Base):
    __tablename__ = "specialties"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), unique=True, nullable=False)
    description = Column(Text)

    doctors = relationship("Doctor", back_populates="specialty")
