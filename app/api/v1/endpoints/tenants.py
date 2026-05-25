from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth import get_tenant, require_roles
from app.database.database import get_db
from app.models import Tenant

router = APIRouter()

SUPPORTED_LANGS = {"es", "en", "pt", "fr", "de", "it"}
SUPPORTED_CURRENCIES = {
    "USD", "EUR", "ARS", "MXN", "BRL", "CLP", "COP", "PEN",
    "UYU", "PYG", "BOB", "VES", "GBP", "CAD", "AUD", "CHF",
}


class TenantOut(BaseModel):
    id: int
    slug: str
    name: str
    plan: str
    status: str
    contact_email: str | None = None
    custom_domain: str | None = None
    timezone: str = "UTC"
    default_currency: str = "USD"
    default_lang: str = "en"
    branding_logo_url: str | None = None
    branding_primary_color: str | None = None
    branding_support_email: str | None = None
    telemedicine_enabled: bool = True
    inventory_enabled: bool = True
    insurance_enabled: bool = True

    class Config:
        from_attributes = True


class TenantUpdate(BaseModel):
    name: str | None = None
    plan: str | None = None
    status: str | None = None
    contact_email: EmailStr | None = None
    custom_domain: str | None = None
    timezone: str | None = None
    default_currency: str | None = None
    default_lang: str | None = None
    branding_logo_url: str | None = None
    branding_primary_color: str | None = None
    branding_support_email: str | None = None
    telemedicine_enabled: bool | None = None
    inventory_enabled: bool | None = None
    insurance_enabled: bool | None = None


class TenantCreate(BaseModel):
    slug: str
    name: str
    plan: str = "starter"
    contact_email: EmailStr | None = None
    timezone: str = "UTC"
    default_currency: str = "USD"
    default_lang: str = "en"


@router.get("/current", response_model=TenantOut)
def current(t=Depends(get_tenant)):
    if not t:
        raise HTTPException(404, "Tenant not resolved")
    return t


@router.get("", response_model=list[TenantOut],
            dependencies=[Depends(require_roles("admin"))])
def list_tenants(db: Session = Depends(get_db)):
    return db.query(Tenant).all()


@router.post("", response_model=TenantOut, status_code=201,
             dependencies=[Depends(require_roles("admin"))])
def create_tenant(payload: TenantCreate, db: Session = Depends(get_db)):
    if payload.default_lang not in SUPPORTED_LANGS:
        raise HTTPException(400, f"Unsupported language. Choose one of: {sorted(SUPPORTED_LANGS)}")
    if payload.default_currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(400, f"Unsupported currency. Choose one of: {sorted(SUPPORTED_CURRENCIES)}")
    existing = db.query(Tenant).filter(Tenant.slug == payload.slug).first()
    if existing:
        raise HTTPException(409, "Slug already in use")
    t = Tenant(**payload.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.patch("/{tid}", response_model=TenantOut,
              dependencies=[Depends(require_roles("admin"))])
def update_tenant(tid: int, payload: TenantUpdate, db: Session = Depends(get_db)):
    t = db.query(Tenant).get(tid)
    if not t:
        raise HTTPException(404, "Not found")
    data = payload.model_dump(exclude_unset=True)
    if "default_lang" in data and data["default_lang"] not in SUPPORTED_LANGS:
        raise HTTPException(400, f"Unsupported language. Choose one of: {sorted(SUPPORTED_LANGS)}")
    if "default_currency" in data and data["default_currency"] not in SUPPORTED_CURRENCIES:
        raise HTTPException(400, f"Unsupported currency. Choose one of: {sorted(SUPPORTED_CURRENCIES)}")
    for k, v in data.items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return t
