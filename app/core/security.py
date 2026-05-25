import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from jose import jwt
from passlib.context import CryptContext

from app.config.settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _create_token(subject: str | int, expires_delta: timedelta, token_type: str,
                  extra: dict[str, Any] | None = None) -> str:
    expire = now_utc() + expires_delta
    payload: dict[str, Any] = {"sub": str(subject), "exp": expire, "type": token_type}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(subject: str | int, role: str,
                        tenant_id: int | None = None) -> str:
    return _create_token(
        subject,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "access",
        {"role": role, "tid": tenant_id},
    )


def create_refresh_token(subject: str | int, jti: str) -> tuple[str, datetime]:
    expires_at = now_utc() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    token = jwt.encode(
        {"sub": str(subject), "exp": expires_at, "type": "refresh", "jti": jti},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return token, expires_at


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def new_jti() -> str:
    return uuid4().hex


def new_random_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
