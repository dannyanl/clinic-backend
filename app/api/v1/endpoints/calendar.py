from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.database.database import get_db
from app.models import Appointment, AppointmentStatus, Doctor, Patient
from app.services.ical_service import doctor_calendar
from app.services import signed_links

router = APIRouter()


@router.get("/doctor/{doctor_id}.ics")
def doctor_ics(doctor_id: int, token: str, db: Session = Depends(get_db)):
    try:
        data = signed_links.verify(token, salt="cal.doctor")
    except ValueError as e:
        raise HTTPException(403, str(e))
    if int(data.get("doctor_id", 0)) != doctor_id:
        raise HTTPException(403, "Token mismatch")

    doctor = db.query(Doctor).options(joinedload(Doctor.user)).get(doctor_id)
    if not doctor:
        raise HTTPException(404, "Not found")

    horizon = datetime.now(timezone.utc) - timedelta(days=30)
    appts = db.query(Appointment).options(
        joinedload(Appointment.patient).joinedload(Patient.user),
    ).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.starts_at >= horizon,
        Appointment.status != AppointmentStatus.CANCELLED.value,
        Appointment.deleted_at.is_(None),
    ).all()

    serialized = [{
        "starts_at": a.starts_at, "ends_at": a.ends_at,
        "patient_name": a.patient.user.full_name if a.patient and a.patient.user else "Paciente",
        "reason": a.reason or "",
        "telemedicine_url": a.telemedicine_url,
    } for a in appts]
    body = doctor_calendar(doctor.user.full_name, serialized)
    return Response(body, media_type="text/calendar")


@router.get("/doctor/{doctor_id}/subscribe-url")
def subscribe_url(doctor_id: int, db: Session = Depends(get_db)):
    if not db.query(Doctor).get(doctor_id):
        raise HTTPException(404, "Not found")
    token = signed_links.make({"doctor_id": doctor_id}, salt="cal.doctor")
    return {"url": f"/api/v1/calendar/doctor/{doctor_id}.ics?token={token}"}
