"""
DeepRare Service — Phase 1: realistic mock.
Phase 2: replace _call_deeprare_api() with actual HTTP call.
"""

import asyncio
import random
from typing import List, Dict, Any

from app.core.config import settings
from app.models.pipeline import DeepRareResult, DiseaseCandidate


async def run_deeprare(
    symptoms: List[str],
    variants: List[Dict[str, Any]],
    suspected_diseases: List[str] | None,
    patient_meta: Dict[str, Any],
) -> DeepRareResult:
    await asyncio.sleep(settings.DEEPRARE_MOCK_DELAY)
    genes = [v.get("gene", "UNKNOWN") for v in variants]
    return _build_mock_result(symptoms, genes, suspected_diseases or [], patient_meta)


def _build_mock_result(
    symptoms: List[str],
    genes: List[str],
    suspected: List[str],
    meta: Dict[str, Any],
) -> DeepRareResult:
    gene_str = genes[0] if genes else "UNKNOWN"

    disease_map = {
        "FBN1": (
            "Marfan Syndrome",
            "ORPHA:558",
            "154700",
            "Autosomal dominant",
            "1/5,000",
        ),
        "BRCA1": (
            "Hereditary Breast and Ovarian Cancer Syndrome",
            "ORPHA:145",
            "604370",
            "Autosomal dominant",
            "1/400",
        ),
        "ATP7B": (
            "Wilson Disease",
            "ORPHA:905",
            "277900",
            "Autosomal recessive",
            "1/30,000",
        ),
        "UNKNOWN": (
            "Unclassified Rare Disease",
            "ORPHA:000",
            None,
            "Unknown",
            "Unknown",
        ),
    }

    primary = disease_map.get(gene_str, disease_map["UNKNOWN"])

    candidates = [
        DiseaseCandidate(
            rank=1,
            disease_name=primary[0],
            orpha_code=primary[1],
            omim_id=primary[2],
            score=round(random.uniform(0.88, 0.97), 3),
            phenotype_match_score=round(random.uniform(0.85, 0.96), 3),
            genotype_match_score=round(random.uniform(0.90, 0.99), 3),
            prevalence=primary[4],
            inheritance_pattern=primary[3],
            matched_symptoms=symptoms[: max(1, len(symptoms) - 1)],
            unmatched_symptoms=symptoms[-1:] if len(symptoms) > 2 else [],
            supporting_genes=[gene_str],
            reasoning=(
                f"Strong phenotype-genotype concordance: {len(symptoms)} HPO terms align with "
                f"{primary[0]} (Orphanet {primary[1]}). The identified variant in {gene_str} "
                f"is a well-established causative gene. gnomAD AF < 0.001 supports pathogenicity. "
                f"Inheritance pattern matches reported familial history."
            ),
        ),
        DiseaseCandidate(
            rank=2,
            disease_name="Loeys-Dietz Syndrome Type 1" if gene_str == "FBN1" else "Familial Adenomatous Polyposis",
            orpha_code="ORPHA:60030" if gene_str == "FBN1" else "ORPHA:733",
            omim_id="609192" if gene_str == "FBN1" else "175100",
            score=round(random.uniform(0.52, 0.68), 3),
            phenotype_match_score=round(random.uniform(0.48, 0.65), 3),
            genotype_match_score=round(random.uniform(0.30, 0.50), 3),
            prevalence="1/50,000",
            inheritance_pattern="Autosomal dominant",
            matched_symptoms=symptoms[: max(1, len(symptoms) // 2)],
            unmatched_symptoms=symptoms[len(symptoms) // 2 :],
            supporting_genes=["TGFBR1", "TGFBR2"] if gene_str == "FBN1" else ["APC"],
            reasoning=(
                "Partial phenotypic overlap, particularly connective tissue features. "
                "However, no pathogenic variant identified in causative genes. "
                "Lower confidence — consider as differential if primary diagnosis is ruled out."
            ),
        ),
        DiseaseCandidate(
            rank=3,
            disease_name="Ehlers-Danlos Syndrome, Classical Type",
            orpha_code="ORPHA:287",
            omim_id="130000",
            score=round(random.uniform(0.25, 0.40), 3),
            phenotype_match_score=round(random.uniform(0.28, 0.42), 3),
            genotype_match_score=round(random.uniform(0.15, 0.30), 3),
            prevalence="1/20,000–40,000",
            inheritance_pattern="Autosomal dominant",
            matched_symptoms=symptoms[:2],
            unmatched_symptoms=symptoms[2:],
            supporting_genes=["COL5A1", "COL5A2"],
            reasoning=(
                "Shared hypermobility and connective tissue features. "
                "Insufficient genotypic evidence. Ranked third as diagnostic alternative."
            ),
        ),
    ]

    return DeepRareResult(
        candidates=candidates,
        total_variants_analyzed=max(1, len(symptoms) + random.randint(2, 8)),
        phenotype_terms_matched=len(symptoms),
        confidence_note=(
            "Mock results — replace with live DeepRare API in Phase 2. "
            "Scores are illustrative and should not guide clinical decisions."
        ),
    )
