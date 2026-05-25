from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from app.database.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True)
    slug = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(160), nullable=False)
    plan = Column(String(32), nullable=False, default="starter")
    status = Column(String(16), nullable=False, default="active")
    contact_email = Column(String(255))
    custom_domain = Column(String(255), unique=True)
    trial_ends_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Internationalization per tenant
    timezone = Column(String(64), nullable=False, server_default="UTC")
    default_currency = Column(String(8), nullable=False, server_default="USD")
    default_lang = Column(String(8), nullable=False, server_default="en")

    # Branding
    branding_logo_url = Column(String(500))
    branding_primary_color = Column(String(16))
    branding_support_email = Column(String(255))

    # Feature flags
    telemedicine_enabled = Column(Boolean, nullable=False, server_default="true")
    inventory_enabled = Column(Boolean, nullable=False, server_default="true")
    insurance_enabled = Column(Boolean, nullable=False, server_default="true")
