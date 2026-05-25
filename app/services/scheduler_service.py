import asyncio
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session, joinedload

from app.config.settings import settings
from app.core.logging import log
from app.core.security import new_random_token
from app.database.database import SessionLocal
from app.models import (
    Appointment, AppointmentStatus, Doctor, NoShowEvent, Patient,
    ReminderPolicy, SurveyResponse, User,
)
from app.services import signed_links
from app.services.notification_service import (
    send_appointment_reminder_with_links, send_sms,
)
from app.services.whatsapp_service import send_whatsapp

scheduler = BackgroundScheduler()


def _send_for_window(db: Session, hours: int, channels: list[str]) -> int:
    now = datetime.now(timezone.utc)
    upper = now + timedelta(hours=hours)
    lower = now + timedelta(hours=hours - 1)
    items = (
        db.query(Appointment)
        .options(
            joinedload(Appointment.doctor).joinedload(Doctor.user),
            joinedload(Appointment.patient).joinedload(Patient.user),
        )
        .filter(Appointment.starts_at >= lower)
        .filter(Appointment.starts_at <= upper)
        .filter(Appointment.deleted_at.is_(None))
        .filter(Appointment.status.in_([
            AppointmentStatus.PENDING.value, AppointmentStatus.CONFIRMED.value,
        ]))
        .filter(Appointment.reminder_sent_at.is_(None))
        .all()
    )
    sent = 0
    for a in items:
        when = a.starts_at.strftime("%d/%m/%Y %H:%M")
        confirm = signed_links.make({"appt_id": a.id}, salt="appt.confirm")
        cancel = signed_links.make({"appt_id": a.id}, salt="appt.cancel")
        confirm_url = f"{settings.PUBLIC_FRONTEND_URL}/api/v1/links/appointment/{quote(confirm)}/confirm"
        cancel_url = f"{settings.PUBLIC_FRONTEND_URL}/api/v1/links/appointment/{quote(cancel)}/cancel"
        try:
            if "email" in channels:
                asyncio.run(send_appointment_reminder_with_links(
                    a.patient.user.email, a.patient.user.full_name,
                    a.doctor.user.full_name, when, confirm_url, cancel_url,
                    user_id=a.patient.user_id,
                ))
            if "sms" in channels and a.patient.user.phone:
                asyncio.run(send_sms(
                    a.patient.user.phone,
                    f"Recordatorio: turno con {a.doctor.user.full_name} {when}.",
                    user_id=a.patient.user_id,
                ))
            if "whatsapp" in channels and a.patient.user.phone:
                asyncio.run(send_whatsapp(
                    a.patient.user.phone,
                    f"Recordatorio: turno con {a.doctor.user.full_name} {when}.",
                    user_id=a.patient.user_id,
                ))
            a.reminder_sent_at = datetime.now(timezone.utc)
            db.commit(); sent += 1
        except Exception as exc:
            log.exception("reminder_failed", appt=a.id, error=str(exc))
    return sent


def reminders_job() -> None:
    db: Session = SessionLocal()
    try:
        policies = db.query(ReminderPolicy).filter(ReminderPolicy.enabled == "true").all()
        if not policies:
            policies = [type("P", (), {"hours_before": 24, "channels": "email"})()]
        for p in policies:
            _send_for_window(db, p.hours_before, [c.strip() for c in p.channels.split(",")])
    finally:
        db.close()


def no_show_job() -> None:
    db: Session = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.NO_SHOW_GRACE_MINUTES)
        items = db.query(Appointment).filter(
            Appointment.starts_at <= cutoff,
            Appointment.status.in_([
                AppointmentStatus.PENDING.value, AppointmentStatus.CONFIRMED.value,
            ]),
            Appointment.deleted_at.is_(None),
        ).all()
        for a in items:
            a.status = AppointmentStatus.NO_SHOW.value
            db.add(NoShowEvent(appointment_id=a.id, patient_id=a.patient_id,
                               fee_charged=settings.NO_SHOW_FEE))
            count = db.query(NoShowEvent).filter(NoShowEvent.patient_id == a.patient_id).count()
            if count >= settings.NO_SHOW_BLOCK_THRESHOLD:
                p = db.query(Patient).get(a.patient_id)
                if p and p.user:
                    p.user.is_blocked = True
        db.commit()
    finally:
        db.close()


def survey_dispatch_job() -> None:
    """Create surveys for completed appointments without one."""
    db: Session = SessionLocal()
    try:
        items = db.query(Appointment).outerjoin(SurveyResponse).filter(
            Appointment.status == AppointmentStatus.COMPLETED.value,
            SurveyResponse.id.is_(None),
            Appointment.deleted_at.is_(None),
        ).limit(50).all()
        for a in items:
            db.add(SurveyResponse(
                appointment_id=a.id, patient_id=a.patient_id,
                token=new_random_token(),
                sent_at=datetime.now(timezone.utc),
            ))
        db.commit()
    finally:
        db.close()


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(reminders_job, IntervalTrigger(minutes=15),
                      id="reminders", replace_existing=True)
    scheduler.add_job(no_show_job, IntervalTrigger(minutes=10),
                      id="no_show", replace_existing=True)
    scheduler.add_job(survey_dispatch_job, IntervalTrigger(hours=1),
                      id="surveys", replace_existing=True)
    scheduler.start()
    log.info("scheduler_started")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
