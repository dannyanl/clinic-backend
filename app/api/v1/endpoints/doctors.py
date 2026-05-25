from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.v1.dependencies.auth import get_current_active_user, require_roles
from app.core.permissions import Role
from app.core.security import hash_password
from app.database.database import get_db
from app.models import Doctor, Specialty, User, Schedule, Absence
from app.schemas import (
    DoctorCreate, DoctorOut, DoctorUpdate,
    ScheduleCreate, ScheduleOut, AbsenceCreate, AbsenceOut,
)

router = APIRouter()


def _to_out(d: Doctor) -> DoctorOut:
    return DoctorOut(
        id=d.id, user_id=d.user_id, license_number=d.license_number,
        bio=d.bio, consultation_fee=d.consultation_fee,
        full_name=d.user.full_name, email=d.user.email, phone=d.user.phone,
        specialty=d.specialty,
    )


@router.get("/", response_model=list[DoctorOut])
def list_doctors(
    db: Session = Depends(get_db),
    specialty_id: int | None = Query(None),
    q: str | None = Query(None, description="Búsqueda por nombre"),
):
    query = db.query(Doctor).options(joinedload(Doctor.user), joinedload(Doctor.specialty))
    if specialty_id:
        query = query.filter(Doctor.specialty_id == specialty_id)
    if q:
        query = query.join(User).filter(User.full_name.ilike(f"%{q}%"))
    return [_to_out(d) for d in query.all()]


@router.get("/{doctor_id}", response_model=DoctorOut)
def get_doctor(doctor_id: int, db: Session = Depends(get_db)):
    d = db.query(Doctor).options(joinedload(Doctor.user), joinedload(Doctor.specialty)).get(doctor_id)
    if not d:
        raise HTTPException(404, "Not found")
    return _to_out(d)


@router.post("/", response_model=DoctorOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_roles(Role.ADMIN))])
def create_doctor(payload: DoctorCreate, db: Session = Depends(get_db)):
    if not db.query(Specialty).get(payload.specialty_id):
        raise HTTPException(400, "Specialty not found")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(409, "Email already in use")
    user = User(
        email=payload.email, full_name=payload.full_name, phone=payload.phone,
        hashed_password=hash_password(payload.password), role=Role.DOCTOR,
    )
    db.add(user); db.flush()
    doc = Doctor(
        user_id=user.id, specialty_id=payload.specialty_id,
        license_number=payload.license_number, bio=payload.bio,
        consultation_fee=payload.consultation_fee,
    )
    db.add(doc); db.commit(); db.refresh(doc)
    return _to_out(doc)


@router.patch("/{doctor_id}", response_model=DoctorOut,
              dependencies=[Depends(require_roles(Role.ADMIN, Role.DOCTOR))])
def update_doctor(doctor_id: int, payload: DoctorUpdate, db: Session = Depends(get_db),
                  me: User = Depends(get_current_active_user)):
    d = db.query(Doctor).get(doctor_id)
    if not d:
        raise HTTPException(404, "Not found")
    if me.role == Role.DOCTOR and d.user_id != me.id:
        raise HTTPException(403, "Forbidden")
    data = payload.model_dump(exclude_unset=True)
    for k in ("full_name", "phone"):
        if k in data:
            setattr(d.user, k, data.pop(k))
    if "is_active" in data and me.role == Role.ADMIN:
        d.user.is_active = data.pop("is_active")
    for k, v in data.items():
        setattr(d, k, v)
    db.commit(); db.refresh(d)
    return _to_out(d)


@router.delete("/{doctor_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_roles(Role.ADMIN))])
def delete_doctor(doctor_id: int, db: Session = Depends(get_db)):
    d = db.query(Doctor).get(doctor_id)
    if not d:
        raise HTTPException(404, "Not found")
    db.delete(d); db.commit()


# ---- Schedules ----

@router.get("/{doctor_id}/schedules", response_model=list[ScheduleOut])
def list_schedules(doctor_id: int, db: Session = Depends(get_db)):
    return db.query(Schedule).filter(Schedule.doctor_id == doctor_id).all()


@router.post("/{doctor_id}/schedules", response_model=ScheduleOut, status_code=201,
             dependencies=[Depends(require_roles(Role.ADMIN, Role.DOCTOR))])
def add_schedule(doctor_id: int, payload: ScheduleCreate, db: Session = Depends(get_db),
                 me: User = Depends(get_current_active_user)):
    doc = db.query(Doctor).get(doctor_id)
    if not doc:
        raise HTTPException(404, "Doctor not found")
    if me.role == Role.DOCTOR and doc.user_id != me.id:
        raise HTTPException(403, "Forbidden")
    s = Schedule(doctor_id=doctor_id, **payload.model_dump())
    db.add(s); db.commit(); db.refresh(s)
    return s


@router.delete("/{doctor_id}/schedules/{schedule_id}", status_code=204,
               dependencies=[Depends(require_roles(Role.ADMIN, Role.DOCTOR))])
def delete_schedule(doctor_id: int, schedule_id: int, db: Session = Depends(get_db)):
    s = db.query(Schedule).filter_by(id=schedule_id, doctor_id=doctor_id).first()
    if not s:
        raise HTTPException(404, "Not found")
    db.delete(s); db.commit()


# ---- Absences ----

@router.get("/{doctor_id}/absences", response_model=list[AbsenceOut])
def list_absences(doctor_id: int, db: Session = Depends(get_db)):
    return db.query(Absence).filter(Absence.doctor_id == doctor_id).all()


@router.post("/{doctor_id}/absences", response_model=AbsenceOut, status_code=201,
             dependencies=[Depends(require_roles(Role.ADMIN, Role.DOCTOR))])
def add_absence(doctor_id: int, payload: AbsenceCreate, db: Session = Depends(get_db)):
    a = Absence(doctor_id=doctor_id, **payload.model_dump())
    db.add(a); db.commit(); db.refresh(a)
    return a
