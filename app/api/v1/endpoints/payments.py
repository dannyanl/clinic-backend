from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth import get_current_active_user, require_roles
from app.core.audit import log_activity
from app.database.database import get_db
from app.models import Appointment, Payment, PaymentProvider, User
from app.schemas import PaymentCreate, PaymentOut
from app.services.payment_service import create_payment, mark_paid

router = APIRouter()


@router.post("", response_model=PaymentOut, status_code=201)
def start_payment(payload: PaymentCreate, request: Request,
                  user: User = Depends(get_current_active_user),
                  db: Session = Depends(get_db)):
    appt = db.query(Appointment).get(payload.appointment_id)
    if not appt:
        raise HTTPException(404, "Appointment not found")
    if db.query(Payment).filter(Payment.appointment_id == appt.id).first():
        raise HTTPException(409, "Payment already exists")
    try:
        provider = PaymentProvider(payload.provider)
    except ValueError:
        raise HTTPException(400, "Invalid provider")
    p = create_payment(
        db, appointment_id=appt.id, amount=payload.amount, currency=payload.currency,
        provider=provider, success_url=payload.success_url or "",
        cancel_url=payload.cancel_url or "",
    )
    log_activity(db, user_id=user.id, action="payment.create",
                 entity="payment", entity_id=p.id, request=request)
    return p


@router.get("/appointment/{appt_id}", response_model=PaymentOut)
def get_payment(appt_id: int, db: Session = Depends(get_db),
                _: User = Depends(get_current_active_user)):
    p = db.query(Payment).filter(Payment.appointment_id == appt_id).first()
    if not p:
        raise HTTPException(404, "Not found")
    return p


@router.post("/{payment_id}/mark-paid", response_model=PaymentOut,
             dependencies=[Depends(require_roles("admin", "receptionist"))])
def manual_mark_paid(payment_id: int, request: Request,
                     user: User = Depends(get_current_active_user),
                     db: Session = Depends(get_db)):
    p = mark_paid(db, payment_id)
    if not p:
        raise HTTPException(404, "Not found")
    log_activity(db, user_id=user.id, action="payment.mark_paid",
                 entity="payment", entity_id=p.id, request=request)
    return p
