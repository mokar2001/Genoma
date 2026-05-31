from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.core.database import Base


class JobType(str, enum.Enum):
    SEQUENCING = "sequencing"        # nf-core FASTQ->VCF
    PIPELINE_INSTALL = "pipeline_install"   # nextflow pull
    DIAGNOSIS = "diagnosis"          # full diagnostic pipeline
    INDEXING = "indexing"            # RareBench -> Qdrant


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _uuid() -> str:
    return str(uuid.uuid4())


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=_uuid)
    case_id = Column(String, ForeignKey("cases.id"), nullable=True)
    celery_task_id = Column(String, nullable=True, index=True)
    job_type = Column(String, nullable=False)
    status = Column(String, default=JobStatus.QUEUED)
    progress = Column(Integer, default=0)
    message = Column(Text, nullable=True)
    params = Column(JSON, default=dict)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    log_path = Column(String, nullable=True)      # path to nextflow / process log
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    case = relationship("Case", back_populates="jobs")


class InstalledPipeline(Base):
    """An nf-core pipeline the user has installed via 'nextflow pull'."""
    __tablename__ = "installed_pipelines"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False, index=True)   # e.g. nf-core/sarek
    revision = Column(String, nullable=True)            # version/tag
    status = Column(String, default="installed")        # installing | installed | failed
    description = Column(Text, nullable=True)
    installed_at = Column(DateTime, default=datetime.utcnow)
