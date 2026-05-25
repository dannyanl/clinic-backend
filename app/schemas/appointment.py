from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class AppointmentCreate(BaseModel):
    doctor_id: int
    patient_id: int | None = None
    starts_at: datetime
    reason: str | None = None
    is_telemedicine: bool = False
    location_id: int | None = None


class AppointmentUpdate(BaseModel):
    starts_at: datetime | None = None
    status: str | None = None
    reason: str | None = None
    notes: str | None = None


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    doctor_id: int
    patient_id: int
    location_id: int | None = None
    starts_at: datetime
    ends_at: datetime
    status: str
    reason: str | None = None
    notes: str | None = None
    is_telemedicine: bool = False
    telemedicine_url: str | None = None
    doctor_name: str | None = None
    patient_name: str | None = None


class AppointmentSlot(BaseModel):
    starts_at: datetime
    ends_at: datetime
    available: bool = True


class AppointmentSeriesCreate(BaseModel):
    doctor_id: int
    patient_id: int | None = None
    weekday: int
    start_time: str  # "HH:MM"
    occurrences: int
    starting_on: date
    reason: str | None = None


class WaitingListCreate(BaseModel):
    doctor_id: int | None = None
    specialty_id: int | None = None
    desired_from: date | None = None
    desired_to: date | None = None
    notes: str | None = None


class WaitingListOut(WaitingListCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    patient_id: int
    status: str
    created_at: datetime
