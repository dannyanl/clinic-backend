from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth import get_current_active_user, require_roles
from app.core.audit import log_activity
from app.database.database import get_db
from app.models import Doctor, MedicalRecord, Patient, Prescription, User
from app.core.phi_audit import log_phi
from app.schemas import MedicalRecordCreate, MedicalRecordOut, MedicalRecordUpdate

router = APIRouter()


def _doctor(user: User, db: Session) -> Doctor:
    d = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if not d:
        raise HTTPException(403, "Doctor profile required")
    return d


@router.get("/patient/{patient_id}", response_model=list[MedicalRecordOut])
def list_for_patient(patient_id: int, db: Session = Depends(get_db),
                     user: User = Depends(get_current_active_user)):
    if user.role == "patient":
        own = db.query(Patient).filter(Patient.user_id == user.id, Patient.id == patient_id).first()
        if not own:
            raise HTTPException(403, "Forbidden")
    rows = (
        db.query(MedicalRecord)
        .filter(MedicalRecord.patient_id == patient_id)
        .order_by(MedicalRecord.created_at.desc())
        .all()
    )
    try:
        log_phi(db, user_id=user.id, patient_id=patient_id, action="view",
                resource="medical_record_list",
                tenant_id=getattr(user, "tenant_id", None))
    except Exception:
        pass
    return rows


@router.post("", response_model=MedicalRecordOut, status_code=201,
             dependencies=[Depends(require_roles("doctor", "admin"))])
def create_record(payload: MedicalRecordCreate, request: Request,
                  user: User = Depends(get_current_active_user),
                  db: Session = Depends(get_db)):
    doctor = _doctor(user, db) if user.role == "doctor" else db.query(Doctor).first()
    if not doctor:
        raise HTTPException(400, "No doctor found")
    rec = MedicalRecord(
        patient_id=payload.patient_id, doctor_id=doctor.id,
        appointment_id=payload.appointment_id,
        chief_complaint=payload.chief_complaint, diagnosis=payload.diagnosis,
        treatment_plan=payload.treatment_plan, notes=payload.notes,
    )
    db.add(rec); db.flush()
    for pr in payload.prescriptions:
        db.add(Prescription(record_id=rec.id, **pr.model_dump()))
    db.commit(); db.refresh(rec)
    try:
        log_phi(db, user_id=user.id, patient_id=rec.patient_id, action="edit", resource="medical_record", resource_id=rec.id, request=request, tenant_id=getattr(user, "tenant_id", None))
    except Exception:
        pass
    log_activity(db, user_id=user.id, action="ehr.create", entity="medical_record", entity_id=rec.id, request=request)
    return rec


@router.patch("/{record_id}", response_model=MedicalRecordOut,
              dependencies=[Depends(require_roles("doctor", "admin"))])
def update_record(record_id: int, payload: MedicalRecordUpdate, request: Request,
                  user: User = Depends(get_current_active_user),
                  db: Session = Depends(get_db)):
    rec = db.query(MedicalRecord).get(record_id)
    if not rec:
        raise HTTPException(404, "Not found")
    data = payload.model_dump(exclude_unset=True)
    prescriptions = data.pop("prescriptions", None)
    for k, v in data.items():
        setattr(rec, k, v)
    if prescriptions is not None:
        db.query(Prescription).filter(Prescription.record_id == rec.id).delete()
        for pr in prescriptions:
            db.add(Prescription(record_id=rec.id, **pr))
    db.commit(); db.refresh(rec)
    try:
        log_phi(db, user_id=user.id, patient_id=rec.patient_id, action="edit", resource="medical_record", resource_id=rec.id, request=request, tenant_id=getattr(user, "tenant_id", None))
    except Exception:
        pass
    log_activity(db, user_id=user.id, action="ehr.update", entity="medical_record", entity_id=rec.id, request=request)
    return rec


@router.get("/{record_id}", response_model=MedicalRecordOut)
def get_record(record_id: int, db: Session = Depends(get_db),
               user: User = Depends(get_current_active_user)):
    rec = db.query(MedicalRecord).get(record_id)
    if not rec:
        raise HTTPException(404, "Not found")
    if user.role == "patient":
        own = db.query(Patient).filter(Patient.user_id == user.id, Patient.id == rec.patient_id).first()
        if not own:
            raise HTTPException(403, "Forbidden")
    try:
        log_phi(db, user_id=user.id, patient_id=rec.patient_id, action="view",
                resource="medical_record", resource_id=rec.id,
                tenant_id=getattr(user, "tenant_id", None))
    except Exception:
        pass
    return rec
