from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth import get_current_active_user, require_roles
from app.core.permissions import Role
from app.database.database import get_db
from app.models import User
from app.schemas import UserOut, UserUpdate

router = APIRouter()


@router.get("/", response_model=list[UserOut], dependencies=[Depends(require_roles(Role.ADMIN))])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), me: User = Depends(get_current_active_user)):
    if me.role != Role.ADMIN and me.id != user_id:
        raise HTTPException(403, "Forbidden")
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(404, "Not found")
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db),
                me: User = Depends(get_current_active_user)):
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(404, "Not found")
    if me.role != Role.ADMIN and me.id != user_id:
        raise HTTPException(403, "Forbidden")
    data = payload.model_dump(exclude_unset=True)
    if me.role != Role.ADMIN:
        data.pop("role", None)
        data.pop("is_active", None)
    for k, v in data.items():
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    return user
