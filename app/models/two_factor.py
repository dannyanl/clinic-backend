from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database.database import Base


class TwoFactorSecret(Base):
    __tablename__ = "two_factor_secrets"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                     unique=True, nullable=False)
    secret = Column(String(64), nullable=False)
    enabled = Column(Boolean, nullable=False, default=False)
    backup_codes = Column(Text)  # JSON list of hashed codes
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    confirmed_at = Column(DateTime(timezone=True))
