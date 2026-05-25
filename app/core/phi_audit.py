from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import PHIAccessLog


def log_phi(db: Session, *, user_id: Optional[int], patient_id: int,
            action: str, resource: str, resource_id: Optional[int] = None,
            purpose: Optional[str] = None, request: Optional[Request] = None,
            tenant_id: Optional[int] = None) -> None:
    db.add(PHIAccessLog(
        tenant_id=tenant_id,
        user_id=user_id,
        patient_id=patient_id,
        action=action,
        resource=resource,
        resource_id=resource_id,
        purpose=purpose,
        ip=(request.client.host if request and request.client else None),
        user_agent=(request.headers.get("user-agent") if request else None),
    ))
    db.commit()
