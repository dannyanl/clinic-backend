from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth import get_current_active_user, require_roles
from app.database.database import get_db
from app.models import InsuranceProvider, Patient, PatientInsurance, User
from app.schemas import (
    InsuranceProviderCreate, InsuranceProviderOut, PatientInsuranceCreate, PatientInsuranceOut,
)

router = APIRouter()


@router.get("/providers", response_model=list[InsuranceProviderOut])
def list_providers(db: Session = Depends(get_db)):
    return db.query(InsuranceProvider).order_by(InsuranceProvider.name).all()


@router.post("/providers", response_model=InsuranceProviderOut, status_code=201,
             dependencies=[Depends(require_roles("admin"))])
def create_provider(payload: InsuranceProviderCreate, db: Session = Depends(get_db)):
    if db.query(InsuranceProvider).filter(InsuranceProvider.name == payload.name).first():
        raise HTTPException(409, "Provider exists")
    obj = InsuranceProvider(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


def _own_patient(user: User, db: Session) -> Patient:
    p = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not p:
        raise HTTPException(404, "Patient profile missing")
    return p


@router.get("/me", response_model=list[PatientInsuranceOut])
def my_insurances(user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    p = _own_patient(user, db)
    return db.query(PatientInsurance).filter(PatientInsurance.patient_id == p.id).all()


@router.post("/me", response_model=PatientInsuranceOut, status_code=201)
def add_my_insurance(payload: PatientInsuranceCreate,
                     user: User = Depends(get_current_active_user),
                     db: Session = Depends(get_db)):
    p = _own_patient(user, db)
    obj = PatientInsurance(patient_id=p.id, **payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


@router.delete("/me/{ins_id}", status_code=204)
def delete_my_insurance(ins_id: int,
                        user: User = Depends(get_current_active_user),
                        db: Session = Depends(get_db)):
    p = _own_patient(user, db)
    obj = db.query(PatientInsurance).filter(
        PatientInsurance.id == ins_id, PatientInsurance.patient_id == p.id,
    ).first()
    if not obj:
        raise HTTPException(404, "Not found")
    db.delete(obj); db.commit()
