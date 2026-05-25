from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth import require_roles
from app.core.permissions import Role
from app.database.database import get_db
from app.models import ActivityLog

router = APIRouter()


@router.get("/logs", dependencies=[Depends(require_roles(Role.ADMIN))])
def list_logs(db: Session = Depends(get_db), limit: int = Query(100, le=500)):
    return (
        db.query(ActivityLog)
        .order_by(ActivityLog.created_at.desc())
        .limit(limit)
        .all()
    )
