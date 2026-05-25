from typing import Iterable, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.security import decode_token
from app.core.tenant_context import resolve_tenant
from app.database.database import get_db
from app.models import Tenant, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


def get_tenant(request: Request, db: Session = Depends(get_db)) -> Optional[Tenant]:
    cached = getattr(request.state, "_tenant_cache", None)
    if cached is not None:
        return cached or None
    t = resolve_tenant(request, db)
    request.state._tenant_cache = t or False
    return t


def require_tenant(t: Optional[Tenant] = Depends(get_tenant)) -> Tenant:
    if not t:
        raise HTTPException(404, "Tenant not found")
    if t.status == "suspended":
        raise HTTPException(403, "Tenant suspended")
    return t


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    cred_exc = HTTPException(status.HTTP_401_UNAUTHORIZED, "Could not validate credentials")
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise cred_exc
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        raise cred_exc
    user = db.query(User).get(user_id)
    if not user:
        raise cred_exc
    # Tenant isolation: token tenant must match resolved tenant when present
    tenant = resolve_tenant(request, db)
    if tenant and user.tenant_id and user.tenant_id != tenant.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Wrong tenant")
    request.state.tenant_id = user.tenant_id
    return user


def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_active or user.deleted_at is not None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Inactive user")
    if getattr(user, "is_blocked", False):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Blocked user")
    return user


def require_roles(*roles: str):
    def _checker(user: User = Depends(get_current_active_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user
    return _checker
