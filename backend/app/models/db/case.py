from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.core.database import Base


class CaseStatus(str, enum.Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class Case(Base):
    __tablename__ = "cases"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    patient_data = Column(JSON, nullable=False)
    status = Column(String, default=CaseStatus.DRAFT)
    result = Column(JSON, nullable=True)
    clinical_notes = Column(Text, nullable=True)
    vcf_filename = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    user = relationship("User", back_populates="cases")
