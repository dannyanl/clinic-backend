from datetime import date, time
from pydantic import BaseModel, ConfigDict, Field


class ScheduleBase(BaseModel):
    weekday: int = Field(ge=0, le=6, description="0=Lunes, 6=Domingo")
    start_time: time
    end_time: time
    slot_minutes: int = 30


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleOut(ScheduleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    doctor_id: int


class AbsenceBase(BaseModel):
    start_date: date
    end_date: date
    reason: str | None = None


class AbsenceCreate(AbsenceBase):
    pass


class AbsenceOut(AbsenceBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    doctor_id: int
