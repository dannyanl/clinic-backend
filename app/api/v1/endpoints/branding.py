from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth import require_roles
from app.config.settings import settings
from app.database.database import get_db
from app.models import Branding

router = APIRouter()


class BrandingIn(BaseModel):
    name: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    support_email: str | None = None


def _get_or_create(db: Session) -> Branding:
    row = db.query(Branding).first()
    if not row:
        row = Branding(
            name=settings.BRAND_NAME, logo_url=settings.BRAND_LOGO_URL,
            primary_color=settings.BRAND_PRIMARY_COLOR,
            support_email=settings.BRAND_SUPPORT_EMAIL,
        )
        db.add(row); db.commit(); db.refresh(row)
    return row


@router.get("")
def get_branding(db: Session = Depends(get_db)):
    b = _get_or_create(db)
    return {"name": b.name, "logo_url": b.logo_url, "primary_color": b.primary_color,
            "support_email": b.support_email}


@router.put("", dependencies=[Depends(require_roles("admin"))])
def update_branding(payload: BrandingIn, db: Session = Depends(get_db)):
    b = _get_or_create(db)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(b, k, v)
    db.commit(); db.refresh(b)
    return {"name": b.name, "logo_url": b.logo_url, "primary_color": b.primary_color,
            "support_email": b.support_email}
