from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.v1.dependencies.auth import get_current_active_user, require_roles
from app.core.permissions import Role
from app.core.security import hash_password
from app.database.database import get_db
from app.models import Patient, User, Appointment
from app.schemas import PatientCreate, PatientOut, PatientUpdate, AppointmentOut

router = APIRouter()


def _to_out(p: Patient) -> PatientOut:
    return PatientOut(
        id=p.id, user_id=p.user_id, dni=p.dni, birth_date=p.birth_date,
        blood_type=p.blood_type, allergies=p.allergies, notes=p.notes,
        full_name=p.user.full_name, email=p.user.email, phone=p.user.phone,
    )


@router.get("/", response_model=list[PatientOut],
            dependencies=[Depends(require_roles(Role.ADMIN, Role.DOCTOR, Role.RECEPTIONIST))])
def list_patients(db: Session = Depends(get_db), q: str | None = Query(None)):
    query = db.query(Patient).options(joinedload(Patient.user)).filter(Patient.deleted_at.is_(None))
    if q:
        query = query.join(User).filter(User.full_name.ilike(f"%{q}%"))
    return [_to_out(p) for p in query.all()]


@router.get("/me", response_model=PatientOut)
def get_me_patient(db: Session = Depends(get_db), me: User = Depends(get_current_active_user)):
    p = db.query(Patient).options(joinedload(Patient.user)).filter(Patient.user_id == me.id).first()
    if not p:
        raise HTTPException(404, "Not a patient")
    return _to_out(p)


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: int, db: Session = Depends(get_db),
                me: User = Depends(get_current_active_user)):
    p = db.query(Patient).options(joinedload(Patient.user)).get(patient_id)
    if not p:
        raise HTTPException(404, "Not found")
    if me.role == Role.PATIENT and p.user_id != me.id:
        raise HTTPException(403, "Forbidden")
    return _to_out(p)


@router.post("/", response_model=PatientOut, status_code=201,
             dependencies=[Depends(require_roles(Role.ADMIN, Role.RECEPTIONIST))])
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(409, "Email in use")
    user = User(
        email=payload.email, full_name=payload.full_name, phone=payload.phone,
        hashed_password=hash_password(payload.password), role=Role.PATIENT,
    )
    db.add(user); db.flush()
    p = Patient(
        user_id=user.id, dni=payload.dni, birth_date=payload.birth_date,
        blood_type=payload.blood_type, allergies=payload.allergies, notes=payload.notes,
    )
    db.add(p); db.commit(); db.refresh(p)
    return _to_out(p)


@router.patch("/{patient_id}", response_model=PatientOut)
def update_patient(patient_id: int, payload: PatientUpdate, db: Session = Depends(get_db),
                   me: User = Depends(get_current_active_user)):
    p = db.query(Patient).get(patient_id)
    if not p:
        raise HTTPException(404, "Not found")
    if me.role == Role.PATIENT and p.user_id != me.id:
        raise HTTPException(403, "Forbidden")
    data = payload.model_dump(exclude_unset=True)
    for k in ("full_name", "phone"):
        if k in data:
            setattr(p.user, k, data.pop(k))
    for k, v in data.items():
        setattr(p, k, v)
    db.commit(); db.refresh(p)
    return _to_out(p)


@router.get("/{patient_id}/history", response_model=list[AppointmentOut],
            dependencies=[Depends(require_roles(Role.ADMIN, Role.DOCTOR, Role.RECEPTIONIST, Role.PATIENT))])
def patient_history(patient_id: int, db: Session = Depends(get_db),
                    me: User = Depends(get_current_active_user)):
    p = db.query(Patient).get(patient_id)
    if not p:
        raise HTTPException(404, "Not found")
    if me.role == Role.PATIENT and p.user_id != me.id:
        raise HTTPException(403, "Forbidden")
    items = (
        db.query(Appointment)
        .options(joinedload(Appointment.doctor).joinedload(p.__class__.user.mapper.class_.__mro__[0]) if False else joinedload(Appointment.doctor))
        .filter(Appointment.patient_id == patient_id)
        .order_by(Appointment.starts_at.desc())
        .all()
    )
    out = []
    for a in items:
        out.append(AppointmentOut(
            id=a.id, doctor_id=a.doctor_id, patient_id=a.patient_id,
            starts_at=a.starts_at, ends_at=a.ends_at, status=a.status,
            reason=a.reason, notes=a.notes,
            doctor_name=a.doctor.user.full_name if a.doctor and a.doctor.user else None,
            patient_name=p.user.full_name,
        ))
    return out


@router.delete("/{patient_id}", status_code=204,
               dependencies=[Depends(require_roles(Role.ADMIN))])
def delete_patient(patient_id: int, db: Session = Depends(get_db)):
    from datetime import datetime, timezone
    p = db.query(Patient).get(patient_id)
    if not p:
        raise HTTPException(404, "Not found")
    now = datetime.now(timezone.utc)
    p.deleted_at = now
    if p.user:
        p.user.deleted_at = now
        p.user.is_active = False
    db.commit()
