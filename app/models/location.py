from sqlalchemy import Column, Integer, String

from app.database.database import Base


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), unique=True, nullable=False)
    address = Column(String(255))
    timezone = Column(String(64), nullable=False, default="America/Argentina/Buenos_Aires")
    phone = Column(String(40))
