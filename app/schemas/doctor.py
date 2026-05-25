from decimal import Decimal
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .specialty import SpecialtyOut


class DoctorBase(BaseModel):
    specialty_id: int
    license_number: str
    bio: str | None = None
    consultation_fee: Decimal = Decimal("0")


class DoctorCreate(DoctorBase):
    email: EmailStr
    full_name: str
    phone: str | None = None
    password: str = Field(min_length=8)


class DoctorUpdate(BaseModel):
    specialty_id: int | None = None
    bio: str | None = None
    consultation_fee: Decimal | None = None
    full_name: str | None = None
    phone: str | None = None
    is_active: bool | None = None


class DoctorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    license_number: str
    bio: str | None = None
    consultation_fee: Decimal
    full_name: str
    email: EmailStr
    phone: str | None = None
    specialty: SpecialtyOut
