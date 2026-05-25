"""Multi-tenant resolution: subdomain (acme.clinic.app) or X-Tenant header.

Stores resolved tenant_id in request.state.tenant_id.
Auth dependency adds it from JWT when present.
"""
from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models import Tenant


def _slug_from_host(host: str) -> Optional[str]:
    if not host:
        return None
    host = host.split(":")[0].lower()
    base = (settings.PUBLIC_BASE_DOMAIN or "").lower()
    if base and host.endswith("." + base):
        return host[: -len(base) - 1]
    return None


def resolve_tenant(request: Request, db: Session) -> Optional[Tenant]:
    # 1) Header
    slug = request.headers.get("X-Tenant-Slug")
    # 2) Subdomain
    if not slug:
        slug = _slug_from_host(request.headers.get("host", ""))
    # 3) Custom domain
    host = (request.headers.get("host") or "").split(":")[0].lower()
    tenant: Optional[Tenant] = None
    if slug:
        tenant = db.query(Tenant).filter(Tenant.slug == slug).first()
    if not tenant and host:
        tenant = db.query(Tenant).filter(Tenant.custom_domain == host).first()
    return tenant
