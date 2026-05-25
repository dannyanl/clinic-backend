from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth import get_current_active_user, require_roles
from app.config.settings import settings
from app.database.database import get_db
from app.models import Attachment, MedicalRecord, Patient, User
from app.schemas import AttachmentOut
from app.services.storage_service import open_for_download, save_upload

router = APIRouter()


@router.post("/upload", response_model=AttachmentOut, status_code=201,
             dependencies=[Depends(require_roles("doctor", "admin", "receptionist"))])
async def upload(
    file: UploadFile = File(...),
    patient_id: int = Form(...),
    record_id: int | None = Form(None),
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"Max upload size is {settings.MAX_UPLOAD_MB}MB")
    file.file.seek(0)
    storage_path, size = save_upload(file, subdir=f"patient_{patient_id}")
    att = Attachment(
        patient_id=patient_id, record_id=record_id,
        filename=file.filename or "file", content_type=file.content_type,
        size_bytes=size, storage_path=storage_path, uploaded_by_id=user.id,
    )
    db.add(att); db.commit(); db.refresh(att)
    return att


@router.get("/{att_id}/download")
def download(att_id: int, db: Session = Depends(get_db),
             user: User = Depends(get_current_active_user)):
    att = db.query(Attachment).get(att_id)
    if not att:
        raise HTTPException(404, "Not found")
    if user.role == "patient":
        own = db.query(Patient).filter(Patient.user_id == user.id, Patient.id == att.patient_id).first()
        if not own:
            raise HTTPException(403, "Forbidden")
    p = open_for_download(att.storage_path)
    return FileResponse(p, filename=att.filename, media_type=att.content_type or "application/octet-stream")


@router.get("/patient/{patient_id}", response_model=list[AttachmentOut])
def list_patient_files(patient_id: int, db: Session = Depends(get_db),
                       user: User = Depends(get_current_active_user)):
    if user.role == "patient":
        own = db.query(Patient).filter(Patient.user_id == user.id, Patient.id == patient_id).first()
        if not own:
            raise HTTPException(403, "Forbidden")
    return db.query(Attachment).filter(Attachment.patient_id == patient_id)\
        .order_by(Attachment.created_at.desc()).all()
