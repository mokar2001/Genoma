"""
Pipeline orchestration Celery tasks.

run_diagnosis: the full per-case flow, executed asynchronously by a worker.

  [optional] FASTQ/BAM -> VCF  (nf-core/sarek)
       -> parse + annotate VCF
       -> phenotype extraction (patient + parents -> HPO)
       -> case similarity (Qdrant / RareBench)
       -> literature crawl (live PubMed/EuropePMC)
       -> variant prioritization (AlphaMissense+gnomAD+ClinVar+Franklin)
       -> structural analysis (AlphaFold) for novel variants
       -> diagnosis synthesis (DeepRare + LLM)
       -> assemble result, persist, index case

Progress is streamed to the browser via Redis pub/sub (app.core.progress).
"""

import asyncio
import logging
from datetime import datetime

from app.core.celery_app import celery
from app.core.database import SessionLocal
from app.core import progress as P
from app.models.db.case import Case, CaseStatus, InputType

logger = logging.getLogger(__name__)


def _set_case(db, case: Case, **fields):
    for k, v in fields.items():
        setattr(case, k, v)
    case.updated_at = datetime.utcnow()
    db.commit()


@celery.task(name="app.tasks.pipeline_tasks.run_diagnosis", bind=True)
def run_diagnosis(self, case_id: str):
    """Entry point — runs the async pipeline in an event loop."""
    return asyncio.run(_run_diagnosis_async(case_id))


async def _run_diagnosis_async(case_id: str):
    db = SessionLocal()
    try:
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return {"error": "case not found"}

        patient = case.patient_data or {}

        def step(stage, status, pct, msg, data=None):
            P.publish(case_id, stage, status, pct, msg, data)
            _set_case(db, case, status=_stage_to_status(stage), progress=pct, stage_message=msg)

        # ── 0. Resolve VCF (sequencing if needed) ─────────────────────────────
        variants = []
        if case.vcf_path:
            step("parsing_vcf", "running", 5, "Parsing VCF…")
            from app.utils.vcf_parser import load_local_vcf
            variants = load_local_vcf(case.vcf_path)
            step("parsing_vcf", "complete", 15,
                 f"{len(variants)} variant(s) parsed.",
                 {"variant_count": len(variants)})
        elif case.input_type == InputType.FASTQ and case.input_files:
            step("sequencing", "running", 8,
                 "Running nf-core/sarek (FASTQ→VCF). This can take a while…")
            from app.services.nfcore_manager import run_sarek
            fastqs = [f["path"] for f in case.input_files]

            def seq_cb(pct, msg):
                P.publish(case_id, "sequencing", "running", 8 + int(pct * 0.2), msg)

            res = run_sarek(case_id, fastqs, progress_cb=seq_cb)
            if not res.get("success") or not res.get("vcf_path"):
                step("sequencing", "error", 0, "Variant calling failed.")
                _set_case(db, case, status=CaseStatus.FAILED,
                          error=(res.get("log") or "sarek failed")[:2000])
                return {"error": "sequencing_failed"}
            _set_case(db, case, vcf_path=res["vcf_path"])
            from app.utils.vcf_parser import load_local_vcf
            variants = load_local_vcf(res["vcf_path"])
            step("sequencing", "complete", 30,
                 f"Sequencing complete — {len(variants)} variant(s).")
        else:
            # No genomic input — symptom-only, use representative variants
            step("parsing_vcf", "complete", 15,
                 "No genomic input — phenotype-only analysis.", {"variant_count": 0})

        # ── 1. Phenotype extraction ───────────────────────────────────────────
        step("phenotype", "running", 35, "Extracting phenotypes → HPO…")
        from app.services.phenotype_extractor import extract_phenotypes, extract_parent_phenotypes
        phenotypes = await extract_phenotypes(
            patient.get("symptoms"), patient.get("clinical_notes"),
        )
        parent_pheno = await extract_parent_phenotypes(patient)
        hpo_names = [p["term"] for p in phenotypes if p.get("term")]
        hpo_ids = [p["hpo_id"] for p in phenotypes if p.get("hpo_id")]
        _set_case(db, case, phenotypes=phenotypes, parent_phenotypes=parent_pheno)
        step("phenotype", "complete", 45,
             f"{len(hpo_ids)} HPO terms resolved.", {"hpo_count": len(hpo_ids)})

        # ── 2. Case similarity (Qdrant) ───────────────────────────────────────
        step("similarity", "running", 50, "Searching similar rare-disease cases…")
        from app.services.case_similarity import search_similar
        similar = search_similar(hpo_names, k=5)
        similar_genes = [s["gene"] for s in similar if s.get("gene")]
        _set_case(db, case, similar_cases=similar)
        step("similarity", "complete", 58,
             f"{len(similar)} similar cases found.", {"similar": similar[:3]})

        # ── 3. Literature crawl ───────────────────────────────────────────────
        step("literature", "running", 60, "Crawling literature (PubMed/EuropePMC)…")
        from app.services.literature_crawler import crawl_literature
        genes = list({(v.get("gene") or "") for v in variants if v.get("gene")})
        literature = await crawl_literature(
            hpo_names, genes, patient.get("suspected_diseases"),
        )
        _set_case(db, case, literature=literature)
        step("literature", "complete", 67,
             f"{len(literature)} relevant articles.", {"count": len(literature)})

        # ── 4. Variant prioritization ─────────────────────────────────────────
        prioritized = []
        if variants:
            step("prioritization", "running", 70,
                 "Prioritizing variants (AlphaMissense+gnomAD+ClinVar)…")
            from app.services.variant_prioritization import prioritize_variants
            prioritized = await prioritize_variants(variants, hpo_names, similar_genes)
            _set_case(db, case, variants=variants, prioritized_variants=prioritized)
            novel = sum(1 for v in prioritized if v.get("novel"))
            step("prioritization", "complete", 80,
                 f"{len(prioritized)} variants ranked, {novel} novel.",
                 {"count": len(prioritized), "novel": novel})

        # ── 5. Structural analysis ────────────────────────────────────────────
        structures = []
        if prioritized:
            step("structure", "running", 82,
                 "Analyzing protein structures (AlphaFold) for novel variants…")
            from app.services.structure_service import analyze_structures
            structures = await analyze_structures(prioritized)
            _set_case(db, case, structures=structures)
            step("structure", "complete", 88,
                 f"{len(structures)} structure(s) analyzed.")

        # ── 6. Diagnosis synthesis ────────────────────────────────────────────
        step("diagnosis", "running", 90, "Synthesizing ranked diagnoses…")
        from app.services.deeprare_service import run_deeprare
        deeprare = await run_deeprare(
            symptoms=hpo_names or (patient.get("symptoms") or []),
            variants=variants,
            suspected_diseases=patient.get("suspected_diseases"),
            patient_meta=patient,
        )

        # ── 7. ACMG (on prioritized variants) ─────────────────────────────────
        from app.services.acmg_service import run_acmg
        acmg = await run_acmg(variants) if variants else None

        # ── Assemble result ───────────────────────────────────────────────────
        result = {
            "session_id": case_id[:8],
            "patient_name": f"{patient.get('first_name','')} {patient.get('last_name','')}".strip(),
            "deeprare": deeprare.model_dump(),
            "acmg": acmg.model_dump() if acmg else None,
            "phenotypes": phenotypes,
            "parent_phenotypes": parent_pheno,
            "similar_cases": similar,
            "literature": literature,
            "prioritized_variants": prioritized,
            "structures": structures,
            "summary": _build_summary(deeprare, prioritized, structures, hpo_ids),
        }
        diagnoses = deeprare.model_dump().get("candidates", [])

        _set_case(
            db, case,
            status=CaseStatus.COMPLETE, progress=100,
            stage_message="Complete",
            diagnoses=diagnoses, result=result,
            completed_at=datetime.utcnow(),
        )
        P.publish(case_id, "complete", "complete", 100, "Pipeline complete.", result)

        # ── Index this case for future similarity search ──────────────────────
        if hpo_names:
            try:
                from app.tasks.indexing_tasks import index_own_case
                top = diagnoses[0]["disease_name"] if diagnoses else ""
                index_own_case.delay({
                    "id": case_id,
                    "hpo_names": hpo_names,
                    "hpo_ids": hpo_ids,
                    "disease": top,
                    "source": "platform",
                    "gene": genes[0] if genes else "",
                })
            except Exception:
                pass

        return {"status": "complete", "case_id": case_id}

    except Exception as e:
        logger.exception("Diagnosis pipeline failed")
        try:
            case = db.query(Case).filter(Case.id == case_id).first()
            if case:
                _set_case(db, case, status=CaseStatus.FAILED, error=str(e)[:2000])
            P.publish(case_id, "error", "error", 0, f"Pipeline error: {e}")
        except Exception:
            pass
        return {"error": str(e)}
    finally:
        db.close()


def _stage_to_status(stage: str) -> str:
    return {
        "sequencing": CaseStatus.SEQUENCING,
        "parsing_vcf": CaseStatus.ANNOTATING,
        "phenotype": CaseStatus.PHENOTYPING,
        "similarity": CaseStatus.SEARCHING,
        "literature": CaseStatus.SEARCHING,
        "prioritization": CaseStatus.PRIORITIZING,
        "structure": CaseStatus.STRUCTURE,
        "diagnosis": CaseStatus.PRIORITIZING,
        "complete": CaseStatus.COMPLETE,
        "error": CaseStatus.FAILED,
    }.get(stage, CaseStatus.PRIORITIZING)


def _build_summary(deeprare, prioritized, structures, hpo_ids) -> str:
    cands = deeprare.model_dump().get("candidates", [])
    top = cands[0] if cands else None
    novel = sum(1 for v in prioritized if v.get("novel"))
    if top:
        s = (f"Top diagnosis: <b>{top['disease_name']}</b> "
             f"(confidence {top['score']:.0%}), based on {len(hpo_ids)} HPO terms")
        if prioritized:
            s += f" and {len(prioritized)} ranked variants"
        if novel:
            s += f", including {novel} novel variant(s) with structural support"
        s += "."
        return s
    return "Phenotype-based analysis complete."


@celery.task(name="app.tasks.pipeline_tasks.install_pipeline_task", bind=True)
def install_pipeline_task(self, name: str, revision: str | None = None):
    """Install an nf-core pipeline via nextflow pull."""
    from app.services.nfcore_manager import install_pipeline

    def cb(pct, msg):
        self.update_state(state="PROGRESS", meta={"progress": pct, "message": msg})

    res = install_pipeline(name, revision, progress_cb=cb)
    return res
