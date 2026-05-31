"""
Cases API — create, list, get, delete, upload genomic files, run pipeline,
stream live progress via SSE.
"""

import os
import json
import shutil
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import settings
from app.core import progress as P
from app.models.db.case import Case, CaseStatus, InputType
from app.models.db.user import User
from app.api.routes.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cases", tags=["cases"])


class CaseCreate(BaseModel):
    title: str
    patient_data: dict


class CaseSummary(BaseModel):
    id: str
    title: str
    status: str
    progress: int
    created_at: datetime
    completed_at: Optional[datetime]
    patient_name: Optional[str]
    top_diagnosis: Optional[str]
    input_type: Optional[str]

    class Config:
        from_attributes = True


@router.get("", response_model=List[CaseSummary])
def list_cases(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cases = (db.query(Case)
             .filter(Case.user_id == user.id)
             .order_by(Case.created_at.desc()).all())
    out = []
    for c in cases:
        pd = c.patient_data or {}
        name = f"{pd.get('first_name','')} {pd.get('last_name','')}".strip() or None
        top = c.diagnoses[0].get("disease_name") if c.diagnoses else None
        out.append(CaseSummary(
            id=c.id, title=c.title, status=c.status, progress=c.progress or 0,
            created_at=c.created_at, completed_at=c.completed_at,
            patient_name=name, top_diagnosis=top, input_type=c.input_type,
        ))
    return out


@router.post("", status_code=201)
def create_case(req: CaseCreate, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    case = Case(user_id=user.id, title=req.title, patient_data=req.patient_data,
                status=CaseStatus.DRAFT)
    db.add(case)
    db.commit()
    db.refresh(case)
    return {"id": case.id, "title": case.title, "status": case.status}


@router.get("/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db),
             user: User = Depends(get_current_user)):
    case = _owned(db, case_id, user)
    return {
        "id": case.id, "title": case.title, "status": case.status,
        "progress": case.progress, "stage_message": case.stage_message,
        "patient_data": case.patient_data, "input_type": case.input_type,
        "input_files": case.input_files, "vcf_path": case.vcf_path,
        "phenotypes": case.phenotypes, "parent_phenotypes": case.parent_phenotypes,
        "similar_cases": case.similar_cases, "literature": case.literature,
        "prioritized_variants": case.prioritized_variants,
        "structures": case.structures, "diagnoses": case.diagnoses,
        "result": case.result, "error": case.error,
        "created_at": case.created_at, "completed_at": case.completed_at,
    }


@router.delete("/{case_id}", status_code=204)
def delete_case(case_id: str, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    case = _owned(db, case_id, user)
    case_dir = os.path.join(settings.DATA_DIR, "cases", case_id)
    if os.path.isdir(case_dir):
        shutil.rmtree(case_dir, ignore_errors=True)
    db.delete(case)
    db.commit()


@router.post("/{case_id}/upload")
async def upload_file(case_id: str, file: UploadFile = File(...),
                      db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    case = _owned(db, case_id, user)
    case_dir = os.path.join(settings.DATA_DIR, "cases", case_id)
    os.makedirs(case_dir, exist_ok=True)
    dest = os.path.join(case_dir, file.filename)

    size = 0
    with open(dest, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)
            size += len(chunk)

    kind = _detect_kind(file.filename)
    files = list(case.input_files or [])
    files.append({"name": file.filename, "path": dest, "size": size, "kind": kind})

    case.input_files = files
    if kind == "vcf":
        case.input_type = InputType.VCF
        case.vcf_path = dest
    elif kind == "fastq":
        case.input_type = InputType.FASTQ
    elif kind == "bam":
        case.input_type = InputType.BAM
    db.commit()

    return {"name": file.filename, "size": size, "kind": kind,
            "input_type": case.input_type}


class RunRequest(BaseModel):
    use_sample: bool = False


@router.post("/{case_id}/run")
def run_case(case_id: str, body: RunRequest | None = None,
             db: Session = Depends(get_db),
             user: User = Depends(get_current_user)):
    case = _owned(db, case_id, user)
    use_sample = bool(body and body.use_sample)

    # When "use sample" is requested, point the case at the server's bundled VCF.
    if use_sample:
        from app.services.sample_data import resolve_sample_vcf
        symptoms = (case.patient_data or {}).get("symptoms", [])
        sample_path = resolve_sample_vcf(symptoms)
        case.vcf_path = sample_path
        case.input_type = "vcf"
        case.vcf_filename = sample_path.split("/")[-1] if sample_path else None

    case.status = CaseStatus.PHENOTYPING
    case.progress = 0
    case.error = None
    db.commit()

    from app.tasks.pipeline_tasks import run_diagnosis
    task = run_diagnosis.delay(case_id, use_sample)
    return {"task_id": task.id, "case_id": case_id, "status": "queued"}


@router.get("/{case_id}/stream")
async def stream_progress(case_id: str, db: Session = Depends(get_db),
                          user: User = Depends(get_current_user)):
    _owned(db, case_id, user)

    async def event_gen():
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe(P.channel(case_id))

        last = P.get_last_state(case_id)
        if last:
            yield f"data: {json.dumps(last)}\n\n"
            if last.get("stage") in ("complete", "error"):
                await pubsub.unsubscribe()
                await r.aclose()
                return

        try:
            while True:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30)
                if msg and msg.get("type") == "message":
                    data = msg["data"]
                    yield f"data: {data}\n\n"
                    evt = json.loads(data)
                    if evt.get("stage") in ("complete", "error"):
                        break
                else:
                    yield ": keepalive\n\n"
        finally:
            await pubsub.unsubscribe()
            await r.aclose()

    return StreamingResponse(event_gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


def _owned(db: Session, case_id: str, user: User) -> Case:
    case = db.query(Case).filter(Case.id == case_id, Case.user_id == user.id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


def _detect_kind(filename: str) -> str:
    f = filename.lower()
    if f.endswith((".vcf", ".vcf.gz")):
        return "vcf"
    if f.endswith((".fastq", ".fastq.gz", ".fq", ".fq.gz")):
        return "fastq"
    if f.endswith((".bam", ".cram")):
        return "bam"
    if f.endswith((".fasta", ".fa", ".fa.gz")):
        return "sequence"
    return "unknown"
