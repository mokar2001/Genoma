from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.core.database import Base


class CaseStatus(str, enum.Enum):
    DRAFT = "draft"                    # created, awaiting input
    UPLOADING = "uploading"           # files being uploaded
    SEQUENCING = "sequencing"         # nf-core FASTQ->VCF running
    ANNOTATING = "annotating"         # VCF annotation
    PHENOTYPING = "phenotyping"       # extracting HPO terms
    SEARCHING = "searching"           # case + literature retrieval
    PRIORITIZING = "prioritizing"     # variant ranking
    STRUCTURE = "structure"           # AlphaFold analysis
    COMPLETE = "complete"
    FAILED = "failed"


class InputType(str, enum.Enum):
    FASTQ = "fastq"          # raw reads — needs alignment + calling
    BAM = "bam"              # aligned — needs variant calling
    VCF = "vcf"              # variants ready
    SEQUENCE = "sequence"    # raw fasta/sequence


def _uuid() -> str:
    return str(uuid.uuid4())


class Case(Base):
    __tablename__ = "cases"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    status = Column(String, default=CaseStatus.DRAFT)

    # ── Patient demographics + clinical (free text + structured) ──────────────
    patient_data = Column(JSON, nullable=False, default=dict)

    # ── Genomic input ─────────────────────────────────────────────────────────
    input_type = Column(String, nullable=True)        # InputType
    input_files = Column(JSON, default=list)          # [{name, path, size, kind}]
    vcf_path = Column(String, nullable=True)          # final VCF (uploaded or produced)
    pipeline_used = Column(String, nullable=True)     # nf-core/sarek, etc.

    # ── Derived results (filled stage by stage) ───────────────────────────────
    phenotypes = Column(JSON, nullable=True)          # [{term, hpo_id, source, score}]
    parent_phenotypes = Column(JSON, nullable=True)   # {father: [...], mother: [...]}
    similar_cases = Column(JSON, nullable=True)       # [{case_id, disease, score}]
    literature = Column(JSON, nullable=True)          # [{title, pmid, url, snippet}]
    variants = Column(JSON, nullable=True)            # parsed variant list
    prioritized_variants = Column(JSON, nullable=True)
    structures = Column(JSON, nullable=True)          # AlphaFold results
    diagnoses = Column(JSON, nullable=True)           # ranked disease candidates
    result = Column(JSON, nullable=True)              # full assembled result

    # ── Metadata ──────────────────────────────────────────────────────────────
    progress = Column(Integer, default=0)             # 0-100
    stage_message = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    clinical_notes = Column(Text, nullable=True)      # kept for back-compat
    vcf_filename = Column(String, nullable=True)      # kept for back-compat
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="cases")
    jobs = relationship("Job", back_populates="case", cascade="all, delete-orphan")
