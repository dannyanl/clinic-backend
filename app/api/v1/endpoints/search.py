from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.api.v1.dependencies.auth import require_roles
from app.database.database import get_db
from app.models import Doctor, Patient, User

router = APIRouter()


@router.get("", dependencies=[Depends(require_roles("admin", "doctor", "receptionist"))])
def search(q: str = Query(..., min_length=2), db: Session = Depends(get_db)):
    like = f"%{q}%"
    patients = (
        db.query(Patient).join(User, User.id == Patient.user_id)
        .filter(Patient.deleted_at.is_(None))
        .filter(or_(User.full_name.ilike(like), User.email.ilike(like),
                    Patient.dni.ilike(like)))
        .limit(20).all()
    )
    doctors = (
        db.query(Doctor).options(joinedload(Doctor.user), joinedload(Doctor.specialty))
        .join(User, User.id == Doctor.user_id)
        .filter(or_(User.full_name.ilike(like), Doctor.license_number.ilike(like)))
        .limit(20).all()
    )
    return {
        "patients": [
            {"id": p.id, "name": p.user.full_name, "email": p.user.email, "dni": p.dni}
            for p in patients
        ],
        "doctors": [
            {"id": d.id, "name": d.user.full_name,
             "specialty": d.specialty.name if d.specialty else None,
             "license": d.license_number}
            for d in doctors
        ],
    }
