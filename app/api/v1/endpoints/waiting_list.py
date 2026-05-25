from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth import get_current_active_user, require_roles
from app.database.database import get_db
from app.models import Patient, User, WaitingListEntry
from app.schemas import WaitingListCreate, WaitingListOut

router = APIRouter()


@router.post("", response_model=WaitingListOut, status_code=201)
def join(payload: WaitingListCreate, user: User = Depends(get_current_active_user),
         db: Session = Depends(get_db)):
    p = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not p:
        raise HTTPException(403, "Patient required")
    entry = WaitingListEntry(patient_id=p.id, **payload.model_dump())
    db.add(entry); db.commit(); db.refresh(entry)
    return entry


@router.get("", response_model=list[WaitingListOut],
            dependencies=[Depends(require_roles("admin", "receptionist", "doctor"))])
def list_all(db: Session = Depends(get_db)):
    return db.query(WaitingListEntry).filter(WaitingListEntry.status == "open").all()


@router.delete("/{entry_id}", status_code=204)
def remove(entry_id: int, user: User = Depends(get_current_active_user),
           db: Session = Depends(get_db)):
    entry = db.query(WaitingListEntry).get(entry_id)
    if not entry:
        raise HTTPException(404, "Not found")
    if user.role == "patient":
        own = db.query(Patient).filter(Patient.user_id == user.id, Patient.id == entry.patient_id).first()
        if not own:
            raise HTTPException(403, "Forbidden")
    db.delete(entry); db.commit()
