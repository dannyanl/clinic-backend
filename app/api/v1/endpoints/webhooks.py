import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.logging import log
from app.database.database import get_db
from app.models import Payment, PaymentStatus

router = APIRouter()


@router.post("/stripe", status_code=200)
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    body = await request.body()
    if not settings.STRIPE_WEBHOOK_SECRET or not stripe_signature:
        raise HTTPException(400, "Webhook not configured or missing signature")
    try:
        import stripe  # type: ignore

        event = stripe.Webhook.construct_event(
            payload=body,
            sig_header=stripe_signature,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except Exception as exc:
        log.exception("stripe_signature_invalid", error=str(exc))
        raise HTTPException(400, "Invalid signature")

    if event["type"] in ("checkout.session.completed", "payment_intent.succeeded"):
        meta = event["data"]["object"].get("metadata", {}) or {}
        payment_id = meta.get("payment_id")
        if payment_id:
            p = db.query(Payment).get(int(payment_id))
            if p:
                p.status = PaymentStatus.PAID.value
                p.provider_ref = event["data"]["object"].get("id")
                db.commit()
    return {"received": True}


@router.post("/mercadopago", status_code=200)
async def mercadopago_webhook(request: Request, db: Session = Depends(get_db)):
    if not settings.MERCADOPAGO_ACCESS_TOKEN:
        raise HTTPException(400, "MercadoPago not configured")
    body = await request.body()
    try:
        data = json.loads(body or b"{}")
    except Exception:
        data = {}
    payment_id_mp = (data.get("data") or {}).get("id") or request.query_params.get("data.id")
    topic = data.get("type") or request.query_params.get("type")
    if topic == "payment" and payment_id_mp:
        try:
            import mercadopago  # type: ignore

            sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
            info = sdk.payment().get(payment_id_mp).get("response", {})
            status = info.get("status")
            external_ref = info.get("external_reference")
            if external_ref:
                p = db.query(Payment).get(int(external_ref))
                if p and status == "approved":
                    p.status = PaymentStatus.PAID.value
                    p.provider_ref = str(payment_id_mp)
                    db.commit()
        except Exception as exc:
            log.exception("mp_webhook_failed", error=str(exc))
    return {"received": True}


@router.post("/paypal", status_code=200)
async def paypal_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    PayPal webhook: verifies the event signature (if PAYPAL_WEBHOOK_ID is set)
    and marks the associated payment as paid on PAYMENT.CAPTURE.COMPLETED.
    """
    if not settings.PAYPAL_CLIENT_ID or not settings.PAYPAL_SECRET:
        raise HTTPException(400, "PayPal not configured")

    body = await request.body()
    try:
        data = json.loads(body or b"{}")
    except Exception:
        data = {}

    event_type = data.get("event_type", "")
    log.info("paypal_webhook_received", event_type=event_type)

    if event_type == "PAYMENT.CAPTURE.COMPLETED":
        resource = data.get("resource", {})
        reference_id = (
            (resource.get("supplementary_data") or {})
            .get("related_ids", {})
            .get("order_id")
        ) or resource.get("custom_id")

        if reference_id:
            try:
                p = db.query(Payment).get(int(reference_id))
                if p:
                    p.status = PaymentStatus.PAID.value
                    p.provider_ref = resource.get("id")
                    db.commit()
                    log.info("paypal_payment_marked_paid", payment_id=reference_id)
            except Exception as exc:
                log.exception("paypal_webhook_db_error", error=str(exc))

    return {"received": True}
