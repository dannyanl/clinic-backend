from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.api.v1.dependencies.auth import get_current_active_user
from app.config.settings import settings
from app.database.database import get_db
from app.models import Doctor, MedicalRecord, Patient, User
from app.services import signed_links
from app.services.pdf_service import prescription_pdf
from app.core.phi_audit import log_phi

router = APIRouter()


@router.get("/{record_id}/pdf")
def record_pdf(record_id: int, db: Session = Depends(get_db),
               user: User = Depends(get_current_active_user)):
    rec = db.query(MedicalRecord).options(
        joinedload(MedicalRecord.patient).joinedload(Patient.user),
        joinedload(MedicalRecord.doctor).joinedload(Doctor.user),
    ).get(record_id)
    if not rec:
        raise HTTPException(404, "Not found")
    if user.role == "patient":
        own = db.query(Patient).filter(
            Patient.user_id == user.id, Patient.id == rec.patient_id,
        ).first()
        if not own:
            raise HTTPException(403, "Forbidden")

    token = signed_links.make({"record_id": rec.id}, salt="rx.verify")
    verify_url = f"{settings.PUBLIC_FRONTEND_URL}/verify-prescription?token={token}"
    pdf = prescription_pdf(
        clinic_name=settings.BRAND_NAME,
        doctor_name=rec.doctor.user.full_name,
        license_no=rec.doctor.license_number,
        patient_name=rec.patient.user.full_name,
        patient_dni=rec.patient.dni,
        prescriptions=[
            {"drug": p.drug, "dosage": p.dosage, "frequency": p.frequency,
             "duration": p.duration, "instructions": p.instructions}
            for p in rec.prescriptions
        ],
        verify_url=verify_url,
    )
    try:
        log_phi(db, user_id=user.id, patient_id=rec.patient_id, action="export", resource="prescription_pdf", resource_id=rec.id, tenant_id=getattr(user, "tenant_id", None))
    except Exception:
        pass
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="receta-{record_id}.pdf"'})
