from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth import get_current_active_user, require_roles
from app.database.database import get_db
from app.models import InventoryItem, InventoryMovement, User

router = APIRouter(dependencies=[Depends(require_roles("admin", "receptionist", "doctor"))])


class ItemIn(BaseModel):
    sku: str
    name: str
    unit: str = "unit"
    location_id: int | None = None
    stock: int = 0
    min_stock: int = 0
    cost: float = 0


class MovementIn(BaseModel):
    delta: int
    reason: str | None = None


@router.get("")
def list_items(db: Session = Depends(get_db), low_only: bool = False):
    q = db.query(InventoryItem)
    rows = q.all()
    if low_only:
        rows = [r for r in rows if r.stock <= r.min_stock]
    return [{"id": r.id, "sku": r.sku, "name": r.name, "unit": r.unit,
             "location_id": r.location_id, "stock": r.stock,
             "min_stock": r.min_stock, "cost": float(r.cost),
             "low": r.stock <= r.min_stock} for r in rows]


@router.post("", status_code=201)
def create_item(payload: ItemIn, db: Session = Depends(get_db)):
    if db.query(InventoryItem).filter(InventoryItem.sku == payload.sku).first():
        raise HTTPException(409, "SKU exists")
    obj = InventoryItem(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return {"id": obj.id}


@router.post("/{item_id}/movement")
def movement(item_id: int, payload: MovementIn, db: Session = Depends(get_db),
             user: User = Depends(get_current_active_user)):
    item = db.query(InventoryItem).get(item_id)
    if not item:
        raise HTTPException(404, "Not found")
    item.stock += payload.delta
    db.add(InventoryMovement(item_id=item.id, delta=payload.delta,
                             reason=payload.reason, user_id=user.id))
    db.commit()
    return {"stock": item.stock}
