from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.api.v1.dependencies.auth import require_roles
from app.database.database import get_db
from app.models import Appointment, Patient, User

router = APIRouter(dependencies=[Depends(require_roles("admin"))])


@router.get("/patients")
def list_deleted_patients(db: Session = Depends(get_db)):
    rows = db.query(Patient).options(joinedload(Patient.user))\
        .filter(Patient.deleted_at.isnot(None)).all()
    return [{"id": p.id, "name": p.user.full_name if p.user else "",
             "deleted_at": p.deleted_at} for p in rows]


@router.post("/patients/{pid}/restore")
def restore_patient(pid: int, db: Session = Depends(get_db)):
    p = db.query(Patient).get(pid)
    if not p:
        raise HTTPException(404, "Not found")
    p.deleted_at = None
    if p.user:
        p.user.deleted_at = None
    db.commit()
    return {"detail": "restored"}


@router.get("/appointments")
def list_deleted_appts(db: Session = Depends(get_db)):
    rows = db.query(Appointment).filter(Appointment.deleted_at.isnot(None)).all()
    return [{"id": a.id, "starts_at": a.starts_at, "deleted_at": a.deleted_at} for a in rows]


@router.post("/appointments/{aid}/restore")
def restore_appt(aid: int, db: Session = Depends(get_db)):
    a = db.query(Appointment).get(aid)
    if not a:
        raise HTTPException(404, "Not found")
    a.deleted_at = None
    db.commit()
    return {"detail": "restored"}
