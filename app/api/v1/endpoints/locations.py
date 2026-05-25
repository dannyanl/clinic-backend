from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth import require_roles
from app.database.database import get_db
from app.models import Location
from app.schemas import LocationCreate, LocationOut, LocationUpdate

router = APIRouter()


@router.get("", response_model=list[LocationOut])
def list_locations(db: Session = Depends(get_db)):
    return db.query(Location).order_by(Location.name).all()


@router.post("", response_model=LocationOut, status_code=201,
             dependencies=[Depends(require_roles("admin"))])
def create_location(payload: LocationCreate, db: Session = Depends(get_db)):
    if db.query(Location).filter(Location.name == payload.name).first():
        raise HTTPException(409, "Location already exists")
    obj = Location(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


@router.patch("/{loc_id}", response_model=LocationOut,
              dependencies=[Depends(require_roles("admin"))])
def update_location(loc_id: int, payload: LocationUpdate, db: Session = Depends(get_db)):
    obj = db.query(Location).get(loc_id)
    if not obj:
        raise HTTPException(404, "Not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit(); db.refresh(obj)
    return obj


@router.delete("/{loc_id}", status_code=204,
               dependencies=[Depends(require_roles("admin"))])
def delete_location(loc_id: int, db: Session = Depends(get_db)):
    obj = db.query(Location).get(loc_id)
    if not obj:
        raise HTTPException(404, "Not found")
    db.delete(obj); db.commit()
