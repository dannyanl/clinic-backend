from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database.database import Base


class MedicalRecordVersion(Base):
    __tablename__ = "medical_record_versions"

    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, ForeignKey("medical_records.id", ondelete="CASCADE"), nullable=False)
    edited_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    snapshot = Column(Text, nullable=False)  # JSON of fields + prescriptions
    action = Column(String(16), nullable=False, default="update")  # create | update | delete
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
