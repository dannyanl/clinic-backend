"""Notification service with multi-language support (ES / EN / PT / FR)."""
from email.message import EmailMessage

import aiosmtplib
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.logging import log
from app.database.database import SessionLocal
from app.models import NotificationLog, NotificationType

# ── Translation strings ───────────────────────────────────────────────────────
_T: dict[str, dict[str, dict[str, str]]] = {
    "appointment_confirmation": {
        "es": {
            "subject": "Confirmación de turno",
            "body": (
                "Hola {patient_name},\n\n"
                "Tu turno con {doctor_name} fue reservado para el {when}.\n"
                "{telemedicine}\n\n"
                "Gracias por usar {brand}."
            ),
            "telemedicine": "Enlace de videoconsulta: {url}",
        },
        "en": {
            "subject": "Appointment Confirmation",
            "body": (
                "Hi {patient_name},\n\n"
                "Your appointment with {doctor_name} has been scheduled for {when}.\n"
                "{telemedicine}\n\n"
                "Thank you for using {brand}."
            ),
            "telemedicine": "Video consultation link: {url}",
        },
        "pt": {
            "subject": "Confirmação de consulta",
            "body": (
                "Olá {patient_name},\n\n"
                "Sua consulta com {doctor_name} foi agendada para {when}.\n"
                "{telemedicine}\n\n"
                "Obrigado por usar {brand}."
            ),
            "telemedicine": "Link da teleconsulta: {url}",
        },
        "fr": {
            "subject": "Confirmation de rendez-vous",
            "body": (
                "Bonjour {patient_name},\n\n"
                "Votre rendez-vous avec {doctor_name} a été confirmé pour le {when}.\n"
                "{telemedicine}\n\n"
                "Merci d'utiliser {brand}."
            ),
            "telemedicine": "Lien de téléconsultation : {url}",
        },
    },
    "appointment_cancellation": {
        "es": {
            "subject": "Cancelación de turno",
            "body": "Hola {patient_name},\n\nTu turno previsto para el {when} fue cancelado.\n\n{brand}",
        },
        "en": {
            "subject": "Appointment Cancelled",
            "body": "Hi {patient_name},\n\nYour appointment scheduled for {when} has been cancelled.\n\n{brand}",
        },
        "pt": {
            "subject": "Consulta cancelada",
            "body": "Olá {patient_name},\n\nSua consulta prevista para {when} foi cancelada.\n\n{brand}",
        },
        "fr": {
            "subject": "Rendez-vous annulé",
            "body": "Bonjour {patient_name},\n\nVotre rendez-vous prévu le {when} a été annulé.\n\n{brand}",
        },
    },
    "appointment_reminder": {
        "es": {
            "subject": "Recordatorio de turno",
            "body": (
                "Hola {patient_name},\n\n"
                "Recordá tu turno con {doctor_name} mañana a las {when}.\n\n"
                "Confirmar: {confirm_url}\nCancelar: {cancel_url}"
            ),
        },
        "en": {
            "subject": "Appointment Reminder",
            "body": (
                "Hi {patient_name},\n\n"
                "This is a reminder for your appointment with {doctor_name} tomorrow at {when}.\n\n"
                "Confirm: {confirm_url}\nCancel: {cancel_url}"
            ),
        },
        "pt": {
            "subject": "Lembrete de consulta",
            "body": (
                "Olá {patient_name},\n\n"
                "Lembrete da sua consulta com {doctor_name} amanhã às {when}.\n\n"
                "Confirmar: {confirm_url}\nCancelar: {cancel_url}"
            ),
        },
        "fr": {
            "subject": "Rappel de rendez-vous",
            "body": (
                "Bonjour {patient_name},\n\n"
                "Rappel de votre rendez-vous avec {doctor_name} demain à {when}.\n\n"
                "Confirmer : {confirm_url}\nAnnuler : {cancel_url}"
            ),
        },
    },
    "password_reset": {
        "es": {
            "subject": "Restablecer contraseña",
            "body": "Hola {full_name},\n\nUsá este enlace para restablecer tu contraseña (válido 1h):\n{reset_url}",
        },
        "en": {
            "subject": "Reset your password",
            "body": "Hi {full_name},\n\nUse this link to reset your password (valid for 1 hour):\n{reset_url}",
        },
        "pt": {
            "subject": "Redefinir senha",
            "body": "Olá {full_name},\n\nUse este link para redefinir sua senha (válido por 1 hora):\n{reset_url}",
        },
        "fr": {
            "subject": "Réinitialisation du mot de passe",
            "body": "Bonjour {full_name},\n\nUtilisez ce lien pour réinitialiser votre mot de passe (valable 1h) :\n{reset_url}",
        },
    },
    "email_verification": {
        "es": {
            "subject": "Verificá tu email",
            "body": "Hola {full_name},\n\nConfirmá tu email visitando:\n{verify_url}",
        },
        "en": {
            "subject": "Verify your email",
            "body": "Hi {full_name},\n\nPlease verify your email by visiting:\n{verify_url}",
        },
        "pt": {
            "subject": "Verifique seu email",
            "body": "Olá {full_name},\n\nVerifique seu email acessando:\n{verify_url}",
        },
        "fr": {
            "subject": "Vérifiez votre email",
            "body": "Bonjour {full_name},\n\nVeuillez vérifier votre adresse email en visitant :\n{verify_url}",
        },
    },
}


def _tr(template: str, lang: str, **kwargs) -> tuple[str, str]:
    """Return (subject, body) for a template in the given language, falling back to 'en'."""
    tmpl = _T.get(template, {})
    strings = tmpl.get(lang) or tmpl.get("en") or {}
    subject = strings.get("subject", template)
    body_tmpl = strings.get("body", "")
    tele_tmpl = strings.get("telemedicine", "")

    telemedicine_line = ""
    if "telemedicine_url" in kwargs and kwargs.get("telemedicine_url"):
        telemedicine_line = tele_tmpl.format(url=kwargs["telemedicine_url"])
    kwargs.setdefault("telemedicine", telemedicine_line)
    kwargs.setdefault("brand", settings.BRAND_NAME)

    body = body_tmpl.format(**{k: v for k, v in kwargs.items() if v is not None})
    return subject, body


# ── Core transport ────────────────────────────────────────────────────────────

def _store(db: Session, *, user_id: int | None, ntype: str, recipient: str,
           subject: str | None, body: str, status: str = "sent", error: str | None = None) -> None:
    db.add(NotificationLog(
        user_id=user_id, type=ntype, recipient=recipient,
        subject=subject, body=body, status=status, error=error,
    ))
    db.commit()


async def send_email(to: str, subject: str, body: str, *, html: str | None = None,
                     user_id: int | None = None) -> None:
    db = SessionLocal()
    try:
        if not settings.SMTP_HOST or not settings.SMTP_FROM:
            log.warning("smtp_not_configured", to=to, subject=subject)
            _store(db, user_id=user_id, ntype=NotificationType.EMAIL.value,
                   recipient=to, subject=subject, body=body,
                   status="skipped", error="SMTP not configured")
            return

        msg = EmailMessage()
        msg["From"] = str(settings.SMTP_FROM)
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        if html:
            msg.add_alternative(html, subtype="html")

        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST, port=settings.SMTP_PORT,
                username=settings.SMTP_USER, password=settings.SMTP_PASSWORD,
                start_tls=settings.SMTP_TLS,
            )
            _store(db, user_id=user_id, ntype=NotificationType.EMAIL.value,
                   recipient=to, subject=subject, body=body)
        except Exception as exc:
            log.exception("email_failed", error=str(exc))
            _store(db, user_id=user_id, ntype=NotificationType.EMAIL.value,
                   recipient=to, subject=subject, body=body, status="failed", error=str(exc))
    finally:
        db.close()


async def send_sms(to: str, body: str, *, user_id: int | None = None) -> None:
    db = SessionLocal()
    try:
        if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM):
            log.warning("twilio_not_configured", to=to)
            _store(db, user_id=user_id, ntype=NotificationType.SMS.value,
                   recipient=to, subject=None, body=body,
                   status="skipped", error="Twilio not configured")
            return
        try:
            from twilio.rest import Client  # type: ignore
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            client.messages.create(to=to, from_=settings.TWILIO_FROM, body=body)
            _store(db, user_id=user_id, ntype=NotificationType.SMS.value,
                   recipient=to, subject=None, body=body)
        except Exception as exc:
            log.exception("sms_failed", error=str(exc))
            _store(db, user_id=user_id, ntype=NotificationType.SMS.value,
                   recipient=to, subject=None, body=body, status="failed", error=str(exc))
    finally:
        db.close()


# ── High-level helpers ────────────────────────────────────────────────────────

async def send_appointment_confirmation(
    to: str, patient_name: str, doctor_name: str, when: str,
    telemedicine_url: str | None = None, user_id: int | None = None,
    lang: str = "en",
) -> None:
    subject, body = _tr(
        "appointment_confirmation", lang,
        patient_name=patient_name, doctor_name=doctor_name,
        when=when, telemedicine_url=telemedicine_url,
    )
    await send_email(to, subject, body, user_id=user_id)


async def send_appointment_cancellation(
    to: str, patient_name: str, when: str,
    user_id: int | None = None, lang: str = "en",
) -> None:
    subject, body = _tr("appointment_cancellation", lang,
                        patient_name=patient_name, when=when)
    await send_email(to, subject, body, user_id=user_id)


async def send_appointment_reminder(
    to: str, patient_name: str, doctor_name: str, when: str,
    user_id: int | None = None, lang: str = "en",
) -> None:
    subject, body = _tr("appointment_reminder", lang,
                        patient_name=patient_name, doctor_name=doctor_name,
                        when=when, confirm_url="", cancel_url="")
    await send_email(to, subject, body, user_id=user_id)


async def send_appointment_reminder_with_links(
    to: str, patient_name: str, doctor_name: str, when: str,
    confirm_url: str, cancel_url: str, *,
    user_id: int | None = None, lang: str = "en",
) -> None:
    subject, body = _tr("appointment_reminder", lang,
                        patient_name=patient_name, doctor_name=doctor_name,
                        when=when, confirm_url=confirm_url, cancel_url=cancel_url)
    await send_email(to, subject, body, user_id=user_id)


async def send_password_reset(
    to: str, full_name: str, reset_url: str,
    user_id: int | None = None, lang: str = "en",
) -> None:
    subject, body = _tr("password_reset", lang, full_name=full_name, reset_url=reset_url)
    await send_email(to, subject, body, user_id=user_id)


async def send_email_verification(
    to: str, full_name: str, verify_url: str,
    user_id: int | None = None, lang: str = "en",
) -> None:
    subject, body = _tr("email_verification", lang, full_name=full_name, verify_url=verify_url)
    await send_email(to, subject, body, user_id=user_id)
