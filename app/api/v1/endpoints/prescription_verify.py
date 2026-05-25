from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database.database import get_db
from app.models import Doctor, MedicalRecord, Patient
from app.services import signed_links

router = APIRouter()


@router.get("/{token}")
def verify(token: str, db: Session = Depends(get_db)):
    try:
        data = signed_links.verify(token, salt="rx.verify")
    except ValueError as e:
        raise HTTPException(400, str(e))
    rec = db.query(MedicalRecord).options(
        joinedload(MedicalRecord.doctor).joinedload(Doctor.user),
        joinedload(MedicalRecord.patient).joinedload(Patient.user),
    ).get(int(data["record_id"]))
    if not rec:
        raise HTTPException(404, "Not found")
    return {
        "valid": True,
        "issued_at": rec.created_at,
        "doctor": rec.doctor.user.full_name if rec.doctor else None,
        "license": rec.doctor.license_number if rec.doctor else None,
        "patient": rec.patient.user.full_name if rec.patient else None,
        "items": [{"drug": p.drug, "dosage": p.dosage, "frequency": p.frequency}
                  for p in rec.prescriptions],
    }
