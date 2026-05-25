from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config.settings import settings


def _serializer(salt: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.SIGNED_LINK_SECRET, salt=salt)


def make(payload: dict, salt: str = "default") -> str:
    return _serializer(salt).dumps(payload)


def verify(token: str, salt: str = "default", max_age_days: int | None = None) -> dict:
    max_age = (max_age_days or settings.SIGNED_LINK_TTL_DAYS) * 86400
    try:
        return _serializer(salt).loads(token, max_age=max_age)
    except SignatureExpired as e:
        raise ValueError("Token expired") from e
    except BadSignature as e:
        raise ValueError("Invalid token") from e
