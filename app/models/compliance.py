from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.database.database import Base


class PHIAccessLog(Base):
    __tablename__ = "phi_access_logs"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    action = Column(String(32), nullable=False)
    resource = Column(String(64), nullable=False)
    resource_id = Column(Integer)
    purpose = Column(String(160))
    ip = Column(String(64))
    user_agent = Column(String(255))
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)


class PrivacyPolicy(Base):
    __tablename__ = "privacy_policies"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    kind = Column(String(32), nullable=False)  # privacy | terms | dpa
    version = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    effective_at = Column(DateTime, server_default=func.now(), nullable=False)
    active = Column(String(8), nullable=False, default="true")

    acceptances = relationship("PolicyAcceptance", back_populates="policy", cascade="all, delete-orphan")


class PolicyAcceptance(Base):
    __tablename__ = "policy_acceptances"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_id = Column(Integer, ForeignKey("privacy_policies.id", ondelete="CASCADE"), nullable=False)
    ip = Column(String(64))
    user_agent = Column(String(255))
    accepted_at = Column(DateTime, server_default=func.now(), nullable=False)

    policy = relationship("PrivacyPolicy", back_populates="acceptances")


class DataExportRequest(Base):
    __tablename__ = "data_export_requests"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(16), nullable=False)  # export | delete
    status = Column(String(16), nullable=False, default="pending")
    notes = Column(Text)
    download_token = Column(String(128))
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime)
