from pydantic import BaseModel, ConfigDict


class SpecialtyBase(BaseModel):
    name: str
    description: str | None = None


class SpecialtyCreate(SpecialtyBase):
    pass


class SpecialtyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class SpecialtyOut(SpecialtyBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
