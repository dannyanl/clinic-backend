from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.v1.dependencies.auth import require_roles
from app.core.permissions import Role
from app.database.database import get_db
from app.models import Appointment, AppointmentStatus, Doctor, Patient, Schedule, User
from app.schemas import (
    OccupancyReport, CancellationReport, RevenueReport, DashboardMetrics,
)

router = APIRouter()


@router.get("/dashboard", response_model=DashboardMetrics,
            dependencies=[Depends(require_roles(Role.ADMIN, Role.RECEPTIONIST))])
def dashboard(db: Session = Depends(get_db)):
    today = datetime.now(timezone.utc).date()
    start_today = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    end_today = start_today + timedelta(days=1)
    month_start = today.replace(day=1)

    appts_today = db.query(func.count(Appointment.id)).filter(
        Appointment.starts_at >= start_today, Appointment.starts_at < end_today
    ).scalar() or 0
    pending = db.query(func.count(Appointment.id)).filter(
        Appointment.status == AppointmentStatus.PENDING.value
    ).scalar() or 0
    revenue = (
        db.query(func.coalesce(func.sum(Doctor.consultation_fee), 0))
        .join(Appointment, Appointment.doctor_id == Doctor.id)
        .filter(Appointment.status == AppointmentStatus.COMPLETED.value)
        .filter(Appointment.starts_at >= datetime.combine(month_start, datetime.min.time(), tzinfo=timezone.utc))
        .scalar()
    ) or Decimal("0")
    return DashboardMetrics(
        total_patients=db.query(func.count(Patient.id)).scalar() or 0,
        total_doctors=db.query(func.count(Doctor.id)).scalar() or 0,
        appointments_today=appts_today,
        appointments_pending=pending,
        revenue_month=revenue,
    )


@router.get("/occupancy", response_model=list[OccupancyReport],
            dependencies=[Depends(require_roles(Role.ADMIN, Role.RECEPTIONIST))])
def occupancy(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
):
    out: list[OccupancyReport] = []
    doctors = db.query(Doctor).options(joinedload(Doctor.user), joinedload(Doctor.schedules)).all()
    for d in doctors:
        total_slots = 0
        for sch in d.schedules:
            cur = date_from
            while cur <= date_to:
                if cur.weekday() == sch.weekday:
                    minutes = (
                        (datetime.combine(cur, sch.end_time) - datetime.combine(cur, sch.start_time)).seconds / 60
                    )
                    total_slots += int(minutes // sch.slot_minutes)
                cur += timedelta(days=1)
        booked = (
            db.query(func.count(Appointment.id))
            .filter(Appointment.doctor_id == d.id)
            .filter(Appointment.status != AppointmentStatus.CANCELLED.value)
            .filter(Appointment.starts_at >= datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc))
            .filter(Appointment.starts_at < datetime.combine(date_to + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc))
            .scalar()
        ) or 0
        rate = (booked / total_slots) if total_slots else 0.0
        out.append(OccupancyReport(
            doctor_id=d.id, doctor_name=d.user.full_name,
            total_slots=total_slots, booked_slots=booked,
            occupancy_rate=round(rate, 4),
        ))
    return out


@router.get("/cancellations", response_model=CancellationReport,
            dependencies=[Depends(require_roles(Role.ADMIN, Role.RECEPTIONIST))])
def cancellations(date_from: date, date_to: date, db: Session = Depends(get_db)):
    base = (
        db.query(Appointment)
        .filter(Appointment.starts_at >= datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc))
        .filter(Appointment.starts_at < datetime.combine(date_to + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc))
    )
    total = base.count()
    cancelled = base.filter(Appointment.status == AppointmentStatus.CANCELLED.value).count()
    no_show = base.filter(Appointment.status == AppointmentStatus.NO_SHOW.value).count()
    rate = (cancelled + no_show) / total if total else 0.0
    return CancellationReport(
        period_start=date_from, period_end=date_to,
        total=total, cancelled=cancelled, no_show=no_show,
        cancellation_rate=round(rate, 4),
    )


@router.get("/revenue", response_model=RevenueReport,
            dependencies=[Depends(require_roles(Role.ADMIN))])
def revenue(date_from: date, date_to: date, db: Session = Depends(get_db)):
    rows = (
        db.query(User.full_name, Doctor.consultation_fee)
        .join(Doctor, Doctor.user_id == User.id)
        .join(Appointment, Appointment.doctor_id == Doctor.id)
        .filter(Appointment.status == AppointmentStatus.COMPLETED.value)
        .filter(Appointment.starts_at >= datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc))
        .filter(Appointment.starts_at < datetime.combine(date_to + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc))
        .all()
    )
    by_doc: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    total = Decimal("0")
    for name, fee in rows:
        by_doc[name] += fee
        total += fee
    return RevenueReport(
        period_start=date_from, period_end=date_to,
        total_revenue=total, by_doctor=dict(by_doc),
    )
