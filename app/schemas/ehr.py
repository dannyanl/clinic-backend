from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PrescriptionBase(BaseModel):
    drug: str
    dosage: str | None = None
    frequency: str | None = None
    duration: str | None = None
    instructions: str | None = None


class PrescriptionCreate(PrescriptionBase):
    pass


class PrescriptionOut(PrescriptionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    content_type: str | None = None
    size_bytes: int | None = None
    created_at: datetime


class MedicalRecordBase(BaseModel):
    chief_complaint: str | None = None
    diagnosis: str | None = None
    treatment_plan: str | None = None
    notes: str | None = None


class MedicalRecordCreate(MedicalRecordBase):
    patient_id: int
    appointment_id: int | None = None
    prescriptions: list[PrescriptionCreate] = []


class MedicalRecordUpdate(MedicalRecordBase):
    prescriptions: list[PrescriptionCreate] | None = None


class MedicalRecordOut(MedicalRecordBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    patient_id: int
    doctor_id: int
    appointment_id: int | None = None
    created_at: datetime
    updated_at: datetime
    prescriptions: list[PrescriptionOut] = []
    attachments: list[AttachmentOut] = []
