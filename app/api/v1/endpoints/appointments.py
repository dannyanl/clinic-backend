from datetime import datetime, time, timedelta, timezone
from urllib.parse import quote
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.api.v1.dependencies.auth import get_current_active_user, require_roles
from app.config.settings import settings
from app.core.audit import log_activity
from app.database.database import get_db
from app.models import (
    Absence, Appointment, AppointmentSeries, AppointmentStatus, Doctor, Patient,
    Schedule, User,
)
from app.schemas import (
    AppointmentCreate, AppointmentOut, AppointmentSeriesCreate, AppointmentSlot,
    AppointmentUpdate,
)
from app.services.notification_service import (
    send_appointment_cancellation, send_appointment_confirmation,
)

router = APIRouter()


def _serialize(a: Appointment) -> AppointmentOut:
    return AppointmentOut(
        id=a.id, doctor_id=a.doctor_id, patient_id=a.patient_id,
        location_id=a.location_id,
        starts_at=a.starts_at, ends_at=a.ends_at, status=a.status,
        reason=a.reason, notes=a.notes,
        is_telemedicine=a.is_telemedicine, telemedicine_url=a.telemedicine_url,
        doctor_name=a.doctor.user.full_name if a.doctor and a.doctor.user else None,
        patient_name=a.patient.user.full_name if a.patient and a.patient.user else None,
    )


def _patient_for_user(user: User, db: Session, override_id: int | None) -> Patient:
    if user.role == "patient":
        p = db.query(Patient).filter(Patient.user_id == user.id).first()
        if not p:
            raise HTTPException(404, "Patient profile missing")
        return p
    if not override_id:
        raise HTTPException(400, "patient_id required")
    p = db.query(Patient).get(override_id)
    if not p:
        raise HTTPException(404, "Patient not found")
    return p


def _slot_minutes(doctor: Doctor, weekday: int) -> int:
    s = next((x for x in doctor.schedules if x.weekday == weekday), None)
    return s.slot_minutes if s else 30


def _has_overlap(db: Session, doctor_id: int, starts_at: datetime, ends_at: datetime,
                 exclude_id: int | None = None) -> bool:
    q = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.status != AppointmentStatus.CANCELLED.value,
        Appointment.deleted_at.is_(None),
        and_(Appointment.starts_at < ends_at, Appointment.ends_at > starts_at),
    )
    if exclude_id:
        q = q.filter(Appointment.id != exclude_id)
    return db.query(q.exists()).scalar()


@router.get("/slots", response_model=list[AppointmentSlot])
def slots(doctor_id: int, day: str, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).options(joinedload(Doctor.schedules)).get(doctor_id)
    if not doctor:
        raise HTTPException(404, "Doctor not found")
    target_date = datetime.fromisoformat(day).date()
    weekday = target_date.weekday()

    if db.query(Absence).filter(
        Absence.doctor_id == doctor_id,
        Absence.start_date <= target_date, Absence.end_date >= target_date,
    ).first():
        return []

    schedule = next((s for s in doctor.schedules if s.weekday == weekday), None)
    if not schedule:
        return []

    out: list[AppointmentSlot] = []
    cur = datetime.combine(target_date, schedule.start_time, tzinfo=timezone.utc)
    end = datetime.combine(target_date, schedule.end_time, tzinfo=timezone.utc)
    delta = timedelta(minutes=schedule.slot_minutes)

    booked = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.starts_at >= cur, Appointment.starts_at < end,
        Appointment.status != AppointmentStatus.CANCELLED.value,
        Appointment.deleted_at.is_(None),
    ).all()
    booked_set = {b.starts_at.replace(tzinfo=timezone.utc) for b in booked}

    while cur + delta <= end:
        out.append(AppointmentSlot(
            starts_at=cur, ends_at=cur + delta,
            available=cur not in booked_set,
        ))
        cur += delta
    return out


@router.post("", response_model=AppointmentOut, status_code=201)
def create_appointment(payload: AppointmentCreate, request: Request,
                       background: BackgroundTasks,
                       user: User = Depends(get_current_active_user),
                       db: Session = Depends(get_db)):
    doctor = db.query(Doctor).options(joinedload(Doctor.user), joinedload(Doctor.schedules))\
        .get(payload.doctor_id)
    if not doctor:
        raise HTTPException(404, "Doctor not found")

    patient = _patient_for_user(user, db, payload.patient_id)
    starts = payload.starts_at if payload.starts_at.tzinfo else payload.starts_at.replace(tzinfo=timezone.utc)
    minutes = _slot_minutes(doctor, starts.weekday())
    ends = starts + timedelta(minutes=minutes)

    if _has_overlap(db, doctor.id, starts, ends):
        raise HTTPException(409, "Slot already taken")

    tele_url = None
    if payload.is_telemedicine:
        room = f"clinic-{uuid4().hex[:12]}"
        tele_url = f"{settings.TELEMEDICINE_BASE_URL}/{quote(room)}"

    appt = Appointment(
        doctor_id=doctor.id, patient_id=patient.id, location_id=payload.location_id,
        starts_at=starts, ends_at=ends, status=AppointmentStatus.PENDING.value,
        reason=payload.reason, is_telemedicine=payload.is_telemedicine,
        telemedicine_url=tele_url,
    )
    db.add(appt); db.commit()
    db.refresh(appt)
    a = db.query(Appointment).options(
        joinedload(Appointment.doctor).joinedload(Doctor.user),
        joinedload(Appointment.patient).joinedload(Patient.user),
    ).get(appt.id)

    background.add_task(
        send_appointment_confirmation,
        a.patient.user.email, a.patient.user.full_name,
        a.doctor.user.full_name, starts.strftime("%d/%m/%Y %H:%M"),
        tele_url, a.patient.user_id,
    )
    log_activity(db, user_id=user.id, action="appointment.create",
                 entity="appointment", entity_id=a.id, request=request)
    return _serialize(a)


@router.post("/series", response_model=list[AppointmentOut], status_code=201,
             dependencies=[Depends(require_roles("doctor", "admin", "receptionist"))])
def create_series(payload: AppointmentSeriesCreate, request: Request,
                  user: User = Depends(get_current_active_user),
                  db: Session = Depends(get_db)):
    doctor = db.query(Doctor).options(joinedload(Doctor.schedules)).get(payload.doctor_id)
    if not doctor:
        raise HTTPException(404, "Doctor not found")
    patient = _patient_for_user(user, db, payload.patient_id)
    series = AppointmentSeries(
        doctor_id=doctor.id, patient_id=patient.id,
        weekday=payload.weekday, start_time=payload.start_time,
        occurrences=payload.occurrences, starting_on=payload.starting_on,
        reason=payload.reason,
    )
    db.add(series); db.flush()

    hh, mm = [int(x) for x in payload.start_time.split(":")]
    minutes = _slot_minutes(doctor, payload.weekday)
    created: list[Appointment] = []
    cur_date = payload.starting_on
    days_ahead = (payload.weekday - cur_date.weekday()) % 7
    cur_date = cur_date + timedelta(days=days_ahead)
    for _ in range(payload.occurrences):
        starts = datetime.combine(cur_date, time(hh, mm), tzinfo=timezone.utc)
        ends = starts + timedelta(minutes=minutes)
        if not _has_overlap(db, doctor.id, starts, ends):
            a = Appointment(
                doctor_id=doctor.id, patient_id=patient.id,
                series_id=series.id, starts_at=starts, ends_at=ends,
                reason=payload.reason, status=AppointmentStatus.PENDING.value,
            )
            db.add(a); created.append(a)
        cur_date += timedelta(days=7)
    db.commit()
    for a in created:
        db.refresh(a)
    log_activity(db, user_id=user.id, action="appointment.series_create",
                 entity="series", entity_id=series.id, request=request,
                 metadata={"created": len(created)})
    rows = db.query(Appointment).options(
        joinedload(Appointment.doctor).joinedload(Doctor.user),
        joinedload(Appointment.patient).joinedload(Patient.user),
    ).filter(Appointment.series_id == series.id).all()
    return [_serialize(x) for x in rows]


@router.get("", response_model=list[AppointmentOut])
def list_appointments(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
    status: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    q = db.query(Appointment).filter(Appointment.deleted_at.is_(None)).options(
        joinedload(Appointment.doctor).joinedload(Doctor.user),
        joinedload(Appointment.patient).joinedload(Patient.user),
    )
    if user.role == "patient":
        p = db.query(Patient).filter(Patient.user_id == user.id).first()
        if not p:
            return []
        q = q.filter(Appointment.patient_id == p.id)
    elif user.role == "doctor":
        d = db.query(Doctor).filter(Doctor.user_id == user.id).first()
        if not d:
            return []
        q = q.filter(Appointment.doctor_id == d.id)

    if status:
        q = q.filter(Appointment.status == status)
    if from_date:
        q = q.filter(Appointment.starts_at >= datetime.fromisoformat(from_date))
    if to_date:
        q = q.filter(Appointment.starts_at <= datetime.fromisoformat(to_date))

    rows = q.order_by(Appointment.starts_at.desc())\
        .offset((page - 1) * page_size).limit(page_size).all()
    return [_serialize(a) for a in rows]


@router.patch("/{appt_id}", response_model=AppointmentOut)
def update_appointment(appt_id: int, payload: AppointmentUpdate,
                       background: BackgroundTasks, request: Request,
                       user: User = Depends(get_current_active_user),
                       db: Session = Depends(get_db)):
    a = db.query(Appointment).options(
        joinedload(Appointment.doctor).joinedload(Doctor.user),
        joinedload(Appointment.patient).joinedload(Patient.user),
    ).get(appt_id)
    if not a:
        raise HTTPException(404, "Not found")

    if user.role == "patient":
        p = db.query(Patient).filter(Patient.user_id == user.id).first()
        if not p or p.id != a.patient_id:
            raise HTTPException(403, "Forbidden")

    data = payload.model_dump(exclude_unset=True)
    if "starts_at" in data and data["starts_at"]:
        starts = data["starts_at"]
        if not starts.tzinfo:
            starts = starts.replace(tzinfo=timezone.utc)
        minutes = _slot_minutes(a.doctor, starts.weekday())
        ends = starts + timedelta(minutes=minutes)
        if _has_overlap(db, a.doctor_id, starts, ends, exclude_id=a.id):
            raise HTTPException(409, "Slot already taken")
        a.starts_at, a.ends_at = starts, ends

    for k in ("status", "reason", "notes"):
        if k in data:
            setattr(a, k, data[k])

    db.commit(); db.refresh(a)

    if data.get("status") == AppointmentStatus.CANCELLED.value:
        background.add_task(
            send_appointment_cancellation,
            a.patient.user.email, a.patient.user.full_name,
            a.starts_at.strftime("%d/%m/%Y %H:%M"), a.patient.user_id,
        )
    log_activity(db, user_id=user.id, action="appointment.update",
                 entity="appointment", entity_id=a.id, request=request, metadata=data)
    return _serialize(a)


@router.post("/{appt_id}/check-in", response_model=AppointmentOut,
             dependencies=[Depends(require_roles("admin", "receptionist", "doctor"))])
def check_in(appt_id: int, request: Request,
             user: User = Depends(get_current_active_user),
             db: Session = Depends(get_db)):
    a = db.query(Appointment).options(
        joinedload(Appointment.doctor).joinedload(Doctor.user),
        joinedload(Appointment.patient).joinedload(Patient.user),
    ).get(appt_id)
    if not a:
        raise HTTPException(404, "Not found")
    a.status = AppointmentStatus.CHECKED_IN.value
    db.commit(); db.refresh(a)
    log_activity(db, user_id=user.id, action="appointment.check_in",
                 entity="appointment", entity_id=a.id, request=request)
    return _serialize(a)

@router.delete("/{appt_id}", status_code=204)
def delete_appointment(appt_id: int, request: Request,
                       user: User = Depends(get_current_active_user),
                       db: Session = Depends(get_db)):
    from datetime import datetime, timezone
    a = db.query(Appointment).get(appt_id)
    if not a:
        raise HTTPException(404, "Not found")
    if user.role == "patient":
        p = db.query(Patient).filter(Patient.user_id == user.id).first()
        if not p or p.id != a.patient_id:
            raise HTTPException(403, "Forbidden")
    a.deleted_at = datetime.now(timezone.utc)
    a.status = AppointmentStatus.CANCELLED.value
    db.commit()
    log_activity(db, user_id=user.id, action="appointment.delete",
                 entity="appointment", entity_id=appt_id, request=request)
