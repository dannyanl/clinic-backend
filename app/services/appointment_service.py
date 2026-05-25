from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import Appointment, AppointmentStatus, Doctor, Schedule, Absence


WEEKDAY_PYTHON_TO_OUR = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6}


def _doctor_or_404(db: Session, doctor_id: int) -> Doctor:
    doctor = db.query(Doctor).get(doctor_id)
    if not doctor:
        raise ValueError("Doctor not found")
    return doctor


def get_available_slots(db: Session, doctor_id: int, day: date) -> list[dict]:
    doctor = _doctor_or_404(db, doctor_id)

    on_absence = (
        db.query(Absence)
        .filter(Absence.doctor_id == doctor.id)
        .filter(Absence.start_date <= day)
        .filter(Absence.end_date >= day)
        .first()
    )
    if on_absence:
        return []

    weekday = WEEKDAY_PYTHON_TO_OUR[day.weekday()]
    schedules = (
        db.query(Schedule)
        .filter(Schedule.doctor_id == doctor.id, Schedule.weekday == weekday)
        .all()
    )

    slots: list[dict] = []
    booked = {
        a.starts_at
        for a in db.query(Appointment)
        .filter(Appointment.doctor_id == doctor.id)
        .filter(Appointment.starts_at >= datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc))
        .filter(Appointment.starts_at < datetime.combine(day + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc))
        .filter(Appointment.status != AppointmentStatus.CANCELLED.value)
        .all()
    }

    for sch in schedules:
        cursor = datetime.combine(day, sch.start_time, tzinfo=timezone.utc)
        end = datetime.combine(day, sch.end_time, tzinfo=timezone.utc)
        delta = timedelta(minutes=sch.slot_minutes)
        while cursor + delta <= end:
            slots.append({
                "starts_at": cursor,
                "ends_at": cursor + delta,
                "available": cursor not in booked,
            })
            cursor += delta
    return slots


def is_slot_available(db: Session, doctor_id: int, starts_at: datetime, slot_minutes: int = 30) -> bool:
    ends_at = starts_at + timedelta(minutes=slot_minutes)
    overlap = (
        db.query(Appointment)
        .filter(Appointment.doctor_id == doctor_id)
        .filter(Appointment.status != AppointmentStatus.CANCELLED.value)
        .filter(Appointment.starts_at < ends_at)
        .filter(Appointment.ends_at > starts_at)
        .first()
    )
    return overlap is None
