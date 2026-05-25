from enum import StrEnum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import relationship

from app.database.database import Base


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentProvider(StrEnum):
    STRIPE = "stripe"
    MERCADOPAGO = "mercadopago"
    PAYPAL = "paypal"
    MANUAL = "manual"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, unique=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(8), nullable=False, default="USD")
    provider = Column(String(32), nullable=False, default=PaymentProvider.MANUAL.value)
    provider_ref = Column(String(255))
    checkout_url = Column(String(500))
    status = Column(String(32), nullable=False, default=PaymentStatus.PENDING.value)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    appointment = relationship("Appointment", back_populates="payment")
