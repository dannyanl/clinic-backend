import json
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import ActivityLog


def log_activity(
    db: Session,
    *,
    user_id: int | None,
    action: str,
    entity: str | None = None,
    entity_id: int | None = None,
    metadata: dict[str, Any] | None = None,
    request: Request | None = None,
) -> None:
    db.add(ActivityLog(
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        metadata_json=json.dumps(metadata) if metadata else None,
        ip=(request.client.host if request and request.client else None),
        user_agent=(request.headers.get("user-agent") if request else None),
    ))
    db.commit()
