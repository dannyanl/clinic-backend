from app.config.settings import settings
from app.core.logging import log
from app.database.database import SessionLocal
from app.models import NotificationLog, NotificationType


def _store(**kw) -> None:
    db = SessionLocal()
    try:
        db.add(NotificationLog(**kw)); db.commit()
    finally:
        db.close()


async def send_whatsapp(to: str, body: str, *, user_id: int | None = None) -> None:
    if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN
            and settings.TWILIO_WHATSAPP_FROM):
        log.warning("twilio_whatsapp_not_configured", to=to)
        _store(user_id=user_id, type="whatsapp", recipient=to, body=body,
               status="skipped", error="WhatsApp not configured")
        return
    try:
        from twilio.rest import Client  # type: ignore

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            from_=f"whatsapp:{settings.TWILIO_WHATSAPP_FROM}",
            to=f"whatsapp:{to}", body=body,
        )
        _store(user_id=user_id, type=NotificationType.SMS.value, recipient=to,
               body=body, status="sent")
    except Exception as exc:
        log.exception("whatsapp_failed", error=str(exc))
        _store(user_id=user_id, type="whatsapp", recipient=to, body=body,
               status="failed", error=str(exc))
