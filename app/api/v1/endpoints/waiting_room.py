from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.api.v1.dependencies.auth import require_roles
from app.database.database import get_db
from app.models import Appointment, AppointmentStatus, Doctor, Patient

router = APIRouter()


@router.get("/today",
            dependencies=[Depends(require_roles("admin", "receptionist", "doctor"))])
def today(db: Session = Depends(get_db),
          location_id: int | None = Query(None)):
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    q = db.query(Appointment).options(
        joinedload(Appointment.doctor).joinedload(Doctor.user),
        joinedload(Appointment.patient).joinedload(Patient.user),
    ).filter(
        Appointment.starts_at >= start, Appointment.starts_at < end,
        Appointment.status.in_([
            AppointmentStatus.CONFIRMED.value, AppointmentStatus.CHECKED_IN.value,
            AppointmentStatus.PENDING.value,
        ]),
    )
    if location_id:
        q = q.filter(Appointment.location_id == location_id)
    rows = q.order_by(Appointment.starts_at).all()
    return [{
        "id": a.id, "starts_at": a.starts_at, "status": a.status,
        "doctor": a.doctor.user.full_name if a.doctor and a.doctor.user else None,
        "patient": a.patient.user.full_name if a.patient and a.patient.user else None,
    } for a in rows]
