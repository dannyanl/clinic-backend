from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth import require_roles
from app.core.permissions import Role
from app.database.database import get_db
from app.models import Specialty
from app.schemas import SpecialtyCreate, SpecialtyOut, SpecialtyUpdate

router = APIRouter()


@router.get("/", response_model=list[SpecialtyOut])
def list_specialties(db: Session = Depends(get_db)):
    return db.query(Specialty).order_by(Specialty.name).all()


@router.post("/", response_model=SpecialtyOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_roles(Role.ADMIN))])
def create_specialty(payload: SpecialtyCreate, db: Session = Depends(get_db)):
    if db.query(Specialty).filter(Specialty.name == payload.name).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Specialty exists")
    s = Specialty(**payload.model_dump())
    db.add(s); db.commit(); db.refresh(s)
    return s


@router.patch("/{specialty_id}", response_model=SpecialtyOut,
              dependencies=[Depends(require_roles(Role.ADMIN))])
def update_specialty(specialty_id: int, payload: SpecialtyUpdate, db: Session = Depends(get_db)):
    s = db.query(Specialty).get(specialty_id)
    if not s:
        raise HTTPException(404, "Not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    db.commit(); db.refresh(s)
    return s


@router.delete("/{specialty_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_roles(Role.ADMIN))])
def delete_specialty(specialty_id: int, db: Session = Depends(get_db)):
    s = db.query(Specialty).get(specialty_id)
    if not s:
        raise HTTPException(404, "Not found")
    db.delete(s); db.commit()
