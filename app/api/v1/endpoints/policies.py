from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth import require_roles
from app.database.database import get_db
from app.models import ReminderPolicy

router = APIRouter(dependencies=[Depends(require_roles("admin"))])


class PolicyIn(BaseModel):
    name: str = "default"
    hours_before: int = 24
    channels: str = "email"
    enabled: str = "true"


@router.get("/reminders")
def list_policies(db: Session = Depends(get_db)):
    rows = db.query(ReminderPolicy).all()
    return [{"id": r.id, "name": r.name, "hours_before": r.hours_before,
             "channels": r.channels, "enabled": r.enabled} for r in rows]


@router.post("/reminders", status_code=201)
def create_policy(payload: PolicyIn, db: Session = Depends(get_db)):
    obj = ReminderPolicy(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return {"id": obj.id}


@router.delete("/reminders/{pid}", status_code=204)
def delete_policy(pid: int, db: Session = Depends(get_db)):
    p = db.query(ReminderPolicy).get(pid)
    if not p:
        raise HTTPException(404, "Not found")
    db.delete(p); db.commit()
