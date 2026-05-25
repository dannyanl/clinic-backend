from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class PaymentCreate(BaseModel):
    appointment_id: int
    amount: Decimal
    currency: str = "ARS"
    provider: str = "manual"
    success_url: str | None = None
    cancel_url: str | None = None


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    appointment_id: int
    amount: Decimal
    currency: str
    provider: str
    status: str
    checkout_url: str | None = None
    provider_ref: str | None = None
    created_at: datetime
