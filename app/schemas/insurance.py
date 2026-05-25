from pydantic import BaseModel, ConfigDict


class InsuranceProviderBase(BaseModel):
    name: str
    code: str | None = None


class InsuranceProviderCreate(InsuranceProviderBase):
    pass


class InsuranceProviderOut(InsuranceProviderBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class PatientInsuranceBase(BaseModel):
    provider_id: int
    membership_number: str
    plan: str | None = None


class PatientInsuranceCreate(PatientInsuranceBase):
    pass


class PatientInsuranceOut(PatientInsuranceBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    patient_id: int
    provider: InsuranceProviderOut
