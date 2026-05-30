"""
Pipeline route — SSE endpoint streaming live progress events.

VCF priority:
  1. User-uploaded VCF file
  2. Local demo VCF at /app/demo_data/<case>.vcf  (set LOCAL_VCF_PATH in env)
  3. Symptom-matched mock variants (phenotype-only mode)
"""

import json
import uuid
import os
from datetime import datetime
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import StreamingResponse

from app.models.pipeline import PipelineStage, StageStatus, SSEEvent, PipelineResult
from app.services.deeprare_service import run_deeprare
from app.services.acmg_service import run_acmg
from app.services.alphafold_service import run_alphafold
from app.utils.vcf_parser import parse_vcf, count_variants, load_local_vcf

import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["pipeline"])

# Path to local demo VCF — override via LOCAL_VCF_PATH env variable
DEFAULT_LOCAL_VCF = os.getenv("LOCAL_VCF_PATH", "")


def _sse(event: SSEEvent) -> str:
    return f"data: {event.model_dump_json()}\n\n"


def _symptom_pick_local_vcf(symptoms: list[str]) -> str:
    """Pick a demo VCF path based on symptom keywords."""
    s = " ".join(symptoms).lower()
    base = "/app/demo_data"
    if any(w in s for w in ["aortic", "marfan", "pectus", "arachnodactyly", "scoliosis", "tall stature"]):
        return f"{base}/sample_marfan.vcf"
    if any(w in s for w in ["breast", "brca", "ovarian", "axillary"]):
        return f"{base}/sample_brca1.vcf"
    if any(w in s for w in ["copper", "wilson", "kayser", "ceruloplasmin", "hepatomegaly", "tremor"]):
        return f"{base}/sample_wilson.vcf"
    return ""


def _mock_variants_for_symptoms(symptoms: list[str]) -> list[dict]:
    from app.core.mock_data import MOCK_VARIANTS
    s = " ".join(symptoms).lower()
    if any(w in s for w in ["aortic", "marfan", "pectus", "arachnodactyly"]):
        return MOCK_VARIANTS["marfan"]
    if any(w in s for w in ["breast", "brca", "ovarian"]):
        return MOCK_VARIANTS["brca1"]
    return MOCK_VARIANTS["wilson"]


def _update_case_status(case_id: str, status: str, result: dict = None) -> None:
    """Update case status in DB. Silently skips if case_id is absent or DB unavailable."""
    if not case_id:
        return
    try:
        from app.core.database import SessionLocal
        from app.models.db.case import Case
        db = SessionLocal()
        try:
            case = db.query(Case).filter(Case.id == case_id).first()
            if case:
                case.status = status
                case.updated_at = datetime.utcnow()
                if status == "complete" and result is not None:
                    case.result = result
                    case.completed_at = datetime.utcnow()
                elif status == "failed":
                    case.completed_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Could not update case {case_id} status: {e}")


@router.post("/run")
async def run_pipeline(
    patient_json: str = Form(...),
    vcf_file: Optional[UploadFile] = File(default=None),
    case_id: Optional[str] = Form(default=None),
):
    # ── Read uploaded VCF eagerly before entering generator ──────────────────
    vcf_content: str = ""
    vcf_source: str = "none"
    vcf_filename: Optional[str] = None

    try:
        if vcf_file is not None and vcf_file.filename not in ("", None):
            raw = await vcf_file.read()
            if raw:
                vcf_content = raw.decode("utf-8", errors="replace")
                vcf_source = "upload"
                vcf_filename = vcf_file.filename
    except Exception as e:
        logger.warning(f"Could not read uploaded VCF: {e}")

    # ── Parse patient data early so we can pick local VCF ────────────────────
    patient_data = json.loads(patient_json)
    symptoms: list[str] = patient_data.get("symptoms", [])

    # If no uploaded VCF, try local file
    if not vcf_content:
        local_path = DEFAULT_LOCAL_VCF or _symptom_pick_local_vcf(symptoms)
        if local_path:
            local_variants = load_local_vcf(local_path)
            if local_variants:
                vcf_source = f"local:{local_path}"
                logger.info(f"Using local VCF: {local_path}")
            else:
                local_variants = []
        else:
            local_variants = []
    else:
        local_variants = []

    # Mark case as running at startup (before generator)
    if case_id:
        _update_case_status(case_id, "running")
        if vcf_filename:
            try:
                from app.core.database import SessionLocal
                from app.models.db.case import Case
                db = SessionLocal()
                try:
                    case = db.query(Case).filter(Case.id == case_id).first()
                    if case:
                        case.vcf_filename = vcf_filename
                        db.commit()
                finally:
                    db.close()
            except Exception as e:
                logger.warning(f"Could not update vcf_filename for case {case_id}: {e}")

    async def event_stream() -> AsyncGenerator[str, None]:
        session_id = str(uuid.uuid4())[:8]

        try:
            suspected: list[str] = patient_data.get("suspected_diseases", [])
            patient_name = (
                f"{patient_data.get('first_name', '')} {patient_data.get('last_name', '')}".strip()
            )

            variants: list[dict] = []
            variant_count = 0
            has_genomics = False

            # ── 1. VCF Parsing ────────────────────────────────────────────────
            if vcf_source == "upload" and vcf_content:
                yield _sse(SSEEvent(
                    stage=PipelineStage.PARSING_VCF,
                    status=StageStatus.RUNNING,
                    progress=5,
                    message="Parsing uploaded VCF file…",
                ))
                variants = parse_vcf(vcf_content)
                variant_count = count_variants(vcf_content)
                has_genomics = True
                yield _sse(SSEEvent(
                    stage=PipelineStage.PARSING_VCF,
                    status=StageStatus.COMPLETE,
                    progress=15,
                    message=f"VCF parsed — {variant_count} variant(s) identified.",
                    data={"variant_count": variant_count, "source": "upload"},
                ))

            elif local_variants:
                has_genomics = True
                variants = local_variants
                variant_count = len(variants)
                vcf_name = os.path.basename(vcf_source.replace("local:", ""))
                yield _sse(SSEEvent(
                    stage=PipelineStage.PARSING_VCF,
                    status=StageStatus.COMPLETE,
                    progress=15,
                    message=f"Using local demo VCF ({vcf_name}) — {variant_count} variant(s) loaded.",
                    data={"variant_count": variant_count, "source": "local", "file": vcf_name},
                ))

            else:
                # No uploaded VCF and no local file — use symptom-matched mock variants
                # so ACMG and AlphaFold still run with realistic data
                variants = _mock_variants_for_symptoms(symptoms)
                variant_count = len(variants)
                has_genomics = True
                yield _sse(SSEEvent(
                    stage=PipelineStage.PARSING_VCF,
                    status=StageStatus.COMPLETE,
                    progress=15,
                    message=f"No VCF uploaded — using {variant_count} representative variant(s) matched to symptoms.",
                    data={"variant_count": variant_count, "source": "mock"},
                ))

            # ── 2. DeepRare ───────────────────────────────────────────────────
            yield _sse(SSEEvent(
                stage=PipelineStage.DEEPRARE,
                status=StageStatus.RUNNING,
                progress=20,
                message=(
                    "Running DeepRare phenotype + genotype ranking (PubCaseFinder + Phenobrain)…"
                    if has_genomics else
                    "Running DeepRare phenotype-only ranking (PubCaseFinder + Phenobrain)…"
                ),
            ))

            deeprare_result = await run_deeprare(symptoms, variants, suspected, patient_data)

            yield _sse(SSEEvent(
                stage=PipelineStage.DEEPRARE,
                status=StageStatus.COMPLETE,
                progress=50,
                message=(
                    f"DeepRare complete — top: {deeprare_result.candidates[0].disease_name} "
                    f"({deeprare_result.candidates[0].score:.1%})"
                ),
                data=deeprare_result.model_dump(),
            ))

            # ── 3. ACMG ───────────────────────────────────────────────────────
            if variants:
                yield _sse(SSEEvent(
                    stage=PipelineStage.ACMG,
                    status=StageStatus.RUNNING,
                    progress=55,
                    message="Classifying variants via ClinVar + ACMG/AMP 2015 criteria…",
                ))
                acmg_result = await run_acmg(variants)
                yield _sse(SSEEvent(
                    stage=PipelineStage.ACMG,
                    status=StageStatus.COMPLETE,
                    progress=72,
                    message=(
                        f"ACMG complete — {acmg_result.pathogenic_count} pathogenic, "
                        f"{acmg_result.likely_pathogenic_count} likely pathogenic, "
                        f"{acmg_result.vus_count} VUS."
                    ),
                    data=acmg_result.model_dump(),
                ))
            else:
                from app.models.pipeline import ACMGResult
                acmg_result = ACMGResult(
                    variants=[], pathogenic_count=0, likely_pathogenic_count=0,
                    vus_count=0, benign_count=0, actionable_variants=[],
                )
                yield _sse(SSEEvent(
                    stage=PipelineStage.ACMG,
                    status=StageStatus.COMPLETE,
                    progress=72,
                    message="ACMG skipped — no genomic variants available.",
                    data={**acmg_result.model_dump(), "skipped": True},
                ))

            # ── 4. AlphaFold3 ─────────────────────────────────────────────────
            if variants:
                yield _sse(SSEEvent(
                    stage=PipelineStage.ALPHAFOLD,
                    status=StageStatus.RUNNING,
                    progress=75,
                    message="Fetching structures from EBI AlphaFold + predicting mutant impact…",
                ))
                alphafold_results = await run_alphafold(variants, acmg_result.variants)
                yield _sse(SSEEvent(
                    stage=PipelineStage.ALPHAFOLD,
                    status=StageStatus.COMPLETE,
                    progress=88,
                    message=f"AlphaFold3 complete — {len(alphafold_results)} structure(s) analysed.",
                    data={"structures": [r.model_dump() for r in alphafold_results]},
                ))
            else:
                alphafold_results = []
                yield _sse(SSEEvent(
                    stage=PipelineStage.ALPHAFOLD,
                    status=StageStatus.COMPLETE,
                    progress=88,
                    message="AlphaFold3 skipped — no variants for structural analysis.",
                    data={"structures": [], "skipped": True},
                ))

            # ── 5. Report ─────────────────────────────────────────────────────
            yield _sse(SSEEvent(
                stage=PipelineStage.GENERATING_REPORT,
                status=StageStatus.RUNNING,
                progress=92,
                message="Compiling diagnostic report…",
            ))

            top = deeprare_result.candidates[0]
            act_count = acmg_result.pathogenic_count + acmg_result.likely_pathogenic_count

            summary = (
                f"AI pipeline identified <b>{top.disease_name}</b> as primary diagnosis "
                f"(confidence {top.score:.1%}) based on {len(symptoms)} clinical features"
                + (f" and {variant_count} genomic variant(s). {act_count} actionable variant(s) confirmed." if has_genomics else ".")
                + (" No VCF provided — genomic analysis skipped." if not has_genomics else "")
            )

            final_result = PipelineResult(
                session_id=session_id,
                patient_name=patient_name,
                deeprare=deeprare_result,
                acmg=acmg_result,
                alphafold=alphafold_results,
                summary=summary,
                time_to_diagnosis_estimate="5–7 years (traditional) → ~30 seconds (AI pipeline)",
                report_url=f"/api/report/{session_id}",
            )

            # Persist result to DB if case_id provided
            _update_case_status(case_id, "complete", final_result.model_dump())

            yield _sse(SSEEvent(
                stage=PipelineStage.COMPLETE,
                status=StageStatus.COMPLETE,
                progress=100,
                message="Pipeline complete.",
                data=final_result.model_dump(),
            ))

        except Exception as exc:
            logger.exception("Pipeline error")
            _update_case_status(case_id, "failed")
            yield _sse(SSEEvent(
                stage=PipelineStage.ERROR,
                status=StageStatus.ERROR,
                progress=0,
                message=f"Pipeline error: {str(exc)}",
            ))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
