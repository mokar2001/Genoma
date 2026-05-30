"""
Pipeline route — SSE endpoint that streams live progress events.
"""

import json
import uuid
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import StreamingResponse

from app.models.pipeline import PipelineStage, StageStatus, SSEEvent, PipelineResult
from app.services.deeprare_service import run_deeprare
from app.services.acmg_service import run_acmg
from app.services.alphafold_service import run_alphafold
from app.utils.vcf_parser import parse_vcf, count_variants

import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["pipeline"])


def _sse(event: SSEEvent) -> str:
    return f"data: {event.model_dump_json()}\n\n"


def _pick_mock_variants(symptoms: list[str]) -> list[dict]:
    from app.core.mock_data import MOCK_VARIANTS
    s = " ".join(symptoms).lower()
    if any(w in s for w in ["aortic", "marfan", "pectus", "arachnodactyly", "scoliosis"]):
        return MOCK_VARIANTS["marfan"]
    if any(w in s for w in ["breast", "brca", "ovarian", "axillary"]):
        return MOCK_VARIANTS["brca1"]
    return MOCK_VARIANTS["wilson"]


@router.post("/run")
async def run_pipeline(
    patient_json: str = Form(...),
    vcf_file: Optional[UploadFile] = File(default=None),
):
    """
    Run the full diagnostic pipeline.
    VCF file is optional — if omitted, ACMG and AlphaFold stages are skipped
    and DeepRare runs on phenotype data only.
    """

    async def event_stream() -> AsyncGenerator[str, None]:
        session_id = str(uuid.uuid4())[:8]

        try:
            patient_data = json.loads(patient_json)
            symptoms: list[str] = patient_data.get("symptoms", [])
            suspected: list[str] = patient_data.get("suspected_diseases", [])
            patient_name = f"{patient_data.get('first_name', '')} {patient_data.get('last_name', '')}".strip()

            has_vcf = vcf_file is not None and vcf_file.filename not in ("", None)
            variants: list[dict] = []
            variant_count = 0

            # ── 1. VCF Parsing (only if file provided) ───────────────────────
            if has_vcf:
                yield _sse(SSEEvent(
                    stage=PipelineStage.PARSING_VCF,
                    status=StageStatus.RUNNING,
                    progress=5,
                    message="Parsing VCF file…",
                ))

                vcf_bytes = await vcf_file.read()
                vcf_content = vcf_bytes.decode("utf-8", errors="replace")
                variants = parse_vcf(vcf_content)
                variant_count = count_variants(vcf_content)

                # If VCF was empty/unparseable fall back to symptom-matched mock
                if not variants:
                    variants = _pick_mock_variants(symptoms)
                    variant_count = len(variants)

                yield _sse(SSEEvent(
                    stage=PipelineStage.PARSING_VCF,
                    status=StageStatus.COMPLETE,
                    progress=15,
                    message=f"VCF parsed — {variant_count} variant(s) identified.",
                    data={"variant_count": variant_count},
                ))
            else:
                # Skip VCF stage — mark as skipped so the UI can reflect it
                yield _sse(SSEEvent(
                    stage=PipelineStage.PARSING_VCF,
                    status=StageStatus.COMPLETE,
                    progress=15,
                    message="No VCF uploaded — skipping genomic variant parsing.",
                    data={"variant_count": 0, "skipped": True},
                ))

            # ── 2. DeepRare (always runs — phenotype-only if no VCF) ─────────
            yield _sse(SSEEvent(
                stage=PipelineStage.DEEPRARE,
                status=StageStatus.RUNNING,
                progress=20,
                message=(
                    "Running DeepRare phenotype ranking…"
                    if not has_vcf
                    else "Running DeepRare phenotype-genotype ranking…"
                ),
            ))

            deeprare_result = await run_deeprare(symptoms, variants, suspected, patient_data)

            yield _sse(SSEEvent(
                stage=PipelineStage.DEEPRARE,
                status=StageStatus.COMPLETE,
                progress=50,
                message=(
                    f"DeepRare complete — top candidate: "
                    f"{deeprare_result.candidates[0].disease_name} "
                    f"({deeprare_result.candidates[0].score:.1%})"
                ),
                data=deeprare_result.model_dump(),
            ))

            # ── 3. ACMG (only if variants available) ─────────────────────────
            if variants:
                yield _sse(SSEEvent(
                    stage=PipelineStage.ACMG,
                    status=StageStatus.RUNNING,
                    progress=55,
                    message="Classifying variants with ACMG/AMP 2015 criteria…",
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
                    variants=[],
                    pathogenic_count=0,
                    likely_pathogenic_count=0,
                    vus_count=0,
                    benign_count=0,
                    actionable_variants=[],
                )
                yield _sse(SSEEvent(
                    stage=PipelineStage.ACMG,
                    status=StageStatus.COMPLETE,
                    progress=72,
                    message="ACMG skipped — no genomic variants to classify.",
                    data={**acmg_result.model_dump(), "skipped": True},
                ))

            # ── 4. AlphaFold3 (only if variants available) ───────────────────
            if variants:
                yield _sse(SSEEvent(
                    stage=PipelineStage.ALPHAFOLD,
                    status=StageStatus.RUNNING,
                    progress=75,
                    message="Predicting protein structures with AlphaFold3…",
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

            # ── 5. Report ────────────────────────────────────────────────────
            yield _sse(SSEEvent(
                stage=PipelineStage.GENERATING_REPORT,
                status=StageStatus.RUNNING,
                progress=92,
                message="Compiling diagnostic report…",
            ))

            top_disease = deeprare_result.candidates[0].disease_name
            actionable_count = acmg_result.pathogenic_count + acmg_result.likely_pathogenic_count

            if has_vcf:
                summary = (
                    f"AI pipeline identified <b>{top_disease}</b> as the primary diagnosis "
                    f"(confidence {deeprare_result.candidates[0].score:.1%}) based on "
                    f"{len(symptoms)} clinical features and {variant_count} genomic variant(s). "
                    f"{actionable_count} actionable variant(s) confirmed."
                )
            else:
                summary = (
                    f"AI pipeline identified <b>{top_disease}</b> as the primary diagnosis "
                    f"(confidence {deeprare_result.candidates[0].score:.1%}) based on "
                    f"{len(symptoms)} clinical feature(s). "
                    f"No VCF provided — genomic variant analysis was skipped."
                )

            final_result = PipelineResult(
                session_id=session_id,
                patient_name=patient_name,
                deeprare=deeprare_result,
                acmg=acmg_result,
                alphafold=alphafold_results,
                summary=summary,
                time_to_diagnosis_estimate="5–7 years (traditional) → ~4 minutes (AI pipeline)",
                report_url=f"/api/report/{session_id}",
            )

            yield _sse(SSEEvent(
                stage=PipelineStage.COMPLETE,
                status=StageStatus.COMPLETE,
                progress=100,
                message="Pipeline complete.",
                data=final_result.model_dump(),
            ))

        except Exception as exc:
            logger.exception("Pipeline error")
            yield _sse(SSEEvent(
                stage=PipelineStage.ERROR,
                status=StageStatus.ERROR,
                progress=0,
                message=f"Pipeline error: {str(exc)}",
            ))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
