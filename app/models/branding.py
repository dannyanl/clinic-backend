from sqlalchemy import Column, DateTime, Integer, String, func

from app.database.database import Base


class Branding(Base):
    __tablename__ = "branding"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, default="Clinic App")
    logo_url = Column(String(500))
    primary_color = Column(String(16), nullable=False, default="#2563eb")
    support_email = Column(String(255))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
