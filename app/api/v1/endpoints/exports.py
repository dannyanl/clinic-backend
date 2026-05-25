from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.api.v1.dependencies.auth import require_roles
from app.database.database import get_db
from app.models import Appointment, Doctor, Patient, User
from app.services.export_service import to_csv, to_xlsx
from app.services.pdf_service import report_pdf

router = APIRouter(dependencies=[Depends(require_roles("admin", "receptionist", "doctor"))])


def _appt_rows(db: Session, from_date: str | None, to_date: str | None):
    q = db.query(Appointment).options(
        joinedload(Appointment.doctor).joinedload(Doctor.user),
        joinedload(Appointment.patient).joinedload(Patient.user),
    )
    if from_date:
        q = q.filter(Appointment.starts_at >= datetime.fromisoformat(from_date))
    if to_date:
        q = q.filter(Appointment.starts_at <= datetime.fromisoformat(to_date))
    rows = []
    for a in q.order_by(Appointment.starts_at).all():
        rows.append([
            a.id,
            a.doctor.user.full_name if a.doctor else "",
            a.patient.user.full_name if a.patient else "",
            a.starts_at.isoformat(),
            a.ends_at.isoformat(),
            a.status, a.reason or "",
        ])
    return rows


HEADERS_APPTS = ["ID", "Profesional", "Paciente", "Inicio", "Fin", "Estado", "Motivo"]


@router.get("/appointments.csv")
def appts_csv(db: Session = Depends(get_db),
              from_date: str | None = None, to_date: str | None = None):
    data = to_csv(HEADERS_APPTS, _appt_rows(db, from_date, to_date))
    return Response(data, media_type="text/csv", headers={
        "Content-Disposition": 'attachment; filename="appointments.csv"',
    })


@router.get("/appointments.xlsx")
def appts_xlsx(db: Session = Depends(get_db),
               from_date: str | None = None, to_date: str | None = None):
    data = to_xlsx(HEADERS_APPTS, _appt_rows(db, from_date, to_date), "Turnos")
    return Response(data,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": 'attachment; filename="appointments.xlsx"'})


@router.get("/appointments.pdf")
def appts_pdf(db: Session = Depends(get_db),
              from_date: str | None = None, to_date: str | None = None):
    rows = [[str(c) for c in r] for r in _appt_rows(db, from_date, to_date)]
    data = report_pdf(title="Listado de turnos", headers=HEADERS_APPTS, rows=rows)
    return Response(data, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="appointments.pdf"'})


@router.get("/patients.csv")
def patients_csv(db: Session = Depends(get_db)):
    rows = []
    for p in db.query(Patient).options(joinedload(Patient.user))\
            .filter(Patient.deleted_at.is_(None)).all():
        rows.append([
            p.id, p.user.full_name if p.user else "", p.user.email if p.user else "",
            p.dni or "", str(p.birth_date) if p.birth_date else "", p.user.phone if p.user else "",
        ])
    data = to_csv(["ID", "Nombre", "Email", "DNI", "Nacimiento", "Tel"], rows)
    return Response(data, media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="patients.csv"'})
