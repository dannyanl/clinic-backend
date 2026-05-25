from pydantic import BaseModel, ConfigDict


class LocationBase(BaseModel):
    name: str
    address: str | None = None
    timezone: str = "America/Argentina/Buenos_Aires"
    phone: str | None = None


class LocationCreate(LocationBase):
    pass


class LocationUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    timezone: str | None = None
    phone: str | None = None


class LocationOut(LocationBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
