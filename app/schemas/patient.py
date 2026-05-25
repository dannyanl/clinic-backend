from datetime import date
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PatientBase(BaseModel):
    dni: str | None = None
    birth_date: date | None = None
    blood_type: str | None = None
    allergies: str | None = None
    notes: str | None = None


class PatientCreate(PatientBase):
    email: EmailStr
    full_name: str
    phone: str | None = None
    password: str = Field(min_length=8)


class PatientUpdate(PatientBase):
    full_name: str | None = None
    phone: str | None = None


class PatientOut(PatientBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    full_name: str
    email: EmailStr
    phone: str | None = None
