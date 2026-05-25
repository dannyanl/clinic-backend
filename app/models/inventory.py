from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, func

from app.database.database import Base


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True)
    sku = Column(String(64), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    unit = Column(String(32), nullable=False, default="unit")
    location_id = Column(Integer, ForeignKey("locations.id"))
    stock = Column(Integer, nullable=False, default=0)
    min_stock = Column(Integer, nullable=False, default=0)
    cost = Column(Numeric(10, 2), nullable=False, default=0)
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False)
    delta = Column(Integer, nullable=False)  # +/-
    reason = Column(String(255))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
