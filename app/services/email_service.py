"""Compat shim. Prefer app.services.notification_service."""
from .notification_service import (  # noqa: F401
    send_email,
    send_appointment_confirmation,
    send_appointment_cancellation,
    send_appointment_reminder,
)
