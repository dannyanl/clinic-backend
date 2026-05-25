"""Startup safety checks — fails fast on insecure defaults in production."""
import sys

from app.config.settings import settings
from app.core.logging import log

_INSECURE_SECRETS = {"change-me", "change-me-signed", "secret", "changeme", ""}
_INSECURE_PASSWORDS = {"Admin1234!", "admin1234", "password", "123456", ""}


def run_startup_checks() -> None:
    if settings.ENVIRONMENT in ("production", "staging"):
        errors: list[str] = []

        if settings.SECRET_KEY in _INSECURE_SECRETS:
            errors.append("SECRET_KEY is set to an insecure default. Set a strong random value.")

        if settings.SIGNED_LINK_SECRET in _INSECURE_SECRETS:
            errors.append("SIGNED_LINK_SECRET is set to an insecure default. Set a strong random value.")

        if settings.FIRST_ADMIN_PASSWORD in _INSECURE_PASSWORDS:
            errors.append(
                "FIRST_ADMIN_PASSWORD is set to a well-known default. "
                "Change it before deploying."
            )

        if not settings.SMTP_HOST:
            log.warning("startup_check_warn", msg="SMTP_HOST not configured — email notifications disabled.")

        if not settings.SENTRY_DSN:
            log.warning("startup_check_warn", msg="SENTRY_DSN not configured — error tracking disabled.")

        if errors:
            for e in errors:
                log.error("startup_check_failed", error=e)
            sys.exit(
                f"STARTUP ABORTED — {len(errors)} security check(s) failed. "
                "Fix the issues above before running in production."
            )

    log.info("startup_checks_passed", env=settings.ENVIRONMENT)
