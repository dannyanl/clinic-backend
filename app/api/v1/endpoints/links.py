from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models import Appointment, AppointmentStatus
from app.services import signed_links

router = APIRouter()


@router.get("/appointment/{token}/confirm")
def confirm(token: str, db: Session = Depends(get_db)):
    try:
        data = signed_links.verify(token, salt="appt.confirm")
    except ValueError as e:
        raise HTTPException(400, str(e))
    a = db.query(Appointment).get(int(data["appt_id"]))
    if not a:
        raise HTTPException(404, "Not found")
    a.status = AppointmentStatus.CONFIRMED.value
    db.commit()
    return {"detail": "Appointment confirmed"}


@router.get("/appointment/{token}/cancel")
def cancel(token: str, db: Session = Depends(get_db)):
    try:
        data = signed_links.verify(token, salt="appt.cancel")
    except ValueError as e:
        raise HTTPException(400, str(e))
    a = db.query(Appointment).get(int(data["appt_id"]))
    if not a:
        raise HTTPException(404, "Not found")
    a.status = AppointmentStatus.CANCELLED.value
    db.commit()
    return {"detail": "Appointment cancelled"}
