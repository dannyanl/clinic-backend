from decimal import Decimal

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.logging import log
from app.models import Payment, PaymentProvider, PaymentStatus


def create_payment(db: Session, *, appointment_id: int, amount: Decimal,
                   currency: str | None = None,
                   provider: PaymentProvider = PaymentProvider.MANUAL,
                   success_url: str = "", cancel_url: str = "") -> Payment:
    resolved_currency = currency or settings.DEFAULT_CURRENCY

    p = Payment(
        appointment_id=appointment_id,
        amount=amount,
        currency=resolved_currency,
        provider=provider.value,
        status=PaymentStatus.PENDING.value,
    )
    db.add(p)
    db.flush()

    if provider == PaymentProvider.STRIPE and settings.STRIPE_SECRET_KEY:
        try:
            import stripe  # type: ignore

            stripe.api_key = settings.STRIPE_SECRET_KEY
            session = stripe.checkout.Session.create(
                mode="payment",
                line_items=[{
                    "price_data": {
                        "currency": resolved_currency.lower(),
                        "product_data": {"name": f"Appointment #{appointment_id}"},
                        "unit_amount": int(amount * 100),
                    },
                    "quantity": 1,
                }],
                success_url=success_url or "https://example.com/ok",
                cancel_url=cancel_url or "https://example.com/cancel",
                metadata={"appointment_id": str(appointment_id), "payment_id": str(p.id)},
            )
            p.checkout_url = session.url
            p.provider_ref = session.id
        except Exception as exc:
            log.exception("stripe_session_failed", error=str(exc))

    elif provider == PaymentProvider.MERCADOPAGO and settings.MERCADOPAGO_ACCESS_TOKEN:
        try:
            import mercadopago  # type: ignore

            sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
            preference = sdk.preference().create({
                "items": [{
                    "title": f"Appointment #{appointment_id}",
                    "quantity": 1,
                    "currency_id": resolved_currency,
                    "unit_price": float(amount),
                }],
                "external_reference": str(p.id),
                "back_urls": {"success": success_url, "failure": cancel_url, "pending": cancel_url},
                "auto_return": "approved",
            })["response"]
            p.checkout_url = preference.get("init_point")
            p.provider_ref = preference.get("id")
        except Exception as exc:
            log.exception("mercadopago_pref_failed", error=str(exc))

    elif provider == PaymentProvider.PAYPAL and settings.PAYPAL_CLIENT_ID and settings.PAYPAL_SECRET:
        try:
            import base64
            import httpx  # type: ignore

            base_url = (
                "https://api-m.sandbox.paypal.com"
                if settings.ENVIRONMENT != "production"
                else "https://api-m.paypal.com"
            )
            credentials = base64.b64encode(
                f"{settings.PAYPAL_CLIENT_ID}:{settings.PAYPAL_SECRET}".encode()
            ).decode()
            token_resp = httpx.post(
                f"{base_url}/v1/oauth2/token",
                headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/x-www-form-urlencoded"},
                data="grant_type=client_credentials",
                timeout=15,
            )
            access_token = token_resp.json()["access_token"]

            order_resp = httpx.post(
                f"{base_url}/v2/checkout/orders",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json={
                    "intent": "CAPTURE",
                    "purchase_units": [{
                        "reference_id": str(p.id),
                        "amount": {"currency_code": resolved_currency, "value": str(amount)},
                        "description": f"Appointment #{appointment_id}",
                    }],
                    "application_context": {
                        "return_url": success_url or "https://example.com/ok",
                        "cancel_url": cancel_url or "https://example.com/cancel",
                    },
                },
                timeout=15,
            )
            order = order_resp.json()
            p.provider_ref = order.get("id")
            for link in order.get("links", []):
                if link.get("rel") == "approve":
                    p.checkout_url = link["href"]
                    break
        except Exception as exc:
            log.exception("paypal_order_failed", error=str(exc))

    db.commit()
    db.refresh(p)
    return p


def mark_paid(db: Session, payment_id: int, provider_ref: str | None = None) -> Payment:
    p = db.query(Payment).get(payment_id)
    if p:
        p.status = PaymentStatus.PAID.value
        if provider_ref:
            p.provider_ref = provider_ref
        db.commit()
    return p
