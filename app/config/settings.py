from typing import List
from pydantic import EmailStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    PROJECT_NAME: str = "Clinix Health Suite"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"

    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    # Internationalization defaults (can be overridden per tenant)
    DEFAULT_TIMEZONE: str = "UTC"
    DEFAULT_CURRENCY: str = "USD"
    DEFAULT_LANG: str = "en"

    DATABASE_URL: str = "postgresql+psycopg2://clinic:clinic@localhost:5432/clinic"
    REDIS_URL: str | None = None

    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:5173"]
    PUBLIC_FRONTEND_URL: str = "http://localhost:5173"
    PUBLIC_BASE_DOMAIN: str = "clinic.local"
    DEFAULT_TENANT_SLUG: str = "demo"
    SALES_DEMO_MODE: bool = True

    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: EmailStr | None = None
    SMTP_TLS: bool = True

    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None
    TWILIO_FROM: str | None = None
    TWILIO_WHATSAPP_FROM: str | None = None

    STRIPE_SECRET_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    MERCADOPAGO_ACCESS_TOKEN: str | None = None
    PAYPAL_CLIENT_ID: str | None = None
    PAYPAL_CLIENT_SECRET: str | None = None

    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_MB: int = 15

    TELEMEDICINE_BASE_URL: str = "https://meet.jit.si"

    SENTRY_DSN: str | None = None

    RATE_LIMIT_LOGIN: str = "10/minute"
    RATE_LIMIT_DEFAULT: str = "120/minute"

    FIRST_ADMIN_EMAIL: EmailStr = "admin@clinic.app"
    FIRST_ADMIN_PASSWORD: str = "Admin1234!"

    TWO_FA_ISSUER: str = "Clinix Health Suite"
    SIGNED_LINK_SECRET: str = "change-me-signed"
    SIGNED_LINK_TTL_DAYS: int = 7

    NO_SHOW_GRACE_MINUTES: int = 20
    NO_SHOW_FEE: float = 0
    NO_SHOW_BLOCK_THRESHOLD: int = 3

    BRAND_NAME: str = "Clinix Health Suite"
    BRAND_LOGO_URL: str = ""
    BRAND_PRIMARY_COLOR: str = "#0ea5e9"
    BRAND_SUPPORT_EMAIL: str = ""

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        return v


settings = Settings()
