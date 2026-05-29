"""
ACMG Classification Service — Phase 1: realistic mock.
Implements ACMG/AMP 2015 classification logic on mocked data.
Phase 2: replace with ClinVar API + local ACMG rule engine.
"""

import asyncio
import random
from typing import List, Dict, Any

from app.core.config import settings
from app.models.pipeline import (
    ACMGResult,
    ACMGClassification,
    ACMGCriterion,
    VariantResult,
)

# Known pathogenic variants database (mock — Phase 2: query ClinVar)
KNOWN_PATHOGENIC = {
    ("FBN1", "c.3463C>T"): ACMGClassification.PATHOGENIC,
    ("BRCA1", "c.5266dupC"): ACMGClassification.PATHOGENIC,
    ("ATP7B", "c.3207C>A"): ACMGClassification.LIKELY_PATHOGENIC,
    ("ATP7B", "c.2755C>T"): ACMGClassification.LIKELY_PATHOGENIC,
}

DISEASE_ASSOCIATIONS = {
    "FBN1": ["Marfan Syndrome", "Ectopia Lentis", "Familial Thoracic Aortic Aneurysm"],
    "BRCA1": ["Hereditary Breast and Ovarian Cancer", "Fanconi Anemia"],
    "ATP7B": ["Wilson Disease", "Hepatolenticular Degeneration"],
}


async def run_acmg(variants: List[Dict[str, Any]]) -> ACMGResult:
    await asyncio.sleep(settings.ACMG_MOCK_DELAY)
    results = [_classify_variant(v) for v in variants]

    pathogenic = sum(1 for r in results if r.classification == ACMGClassification.PATHOGENIC)
    likely_path = sum(1 for r in results if r.classification == ACMGClassification.LIKELY_PATHOGENIC)
    vus = sum(1 for r in results if r.classification == ACMGClassification.VUS)
    benign = sum(1 for r in results if r.classification in (ACMGClassification.BENIGN, ACMGClassification.LIKELY_BENIGN))

    actionable = [
        r.variant_id
        for r in results
        if r.classification in (ACMGClassification.PATHOGENIC, ACMGClassification.LIKELY_PATHOGENIC)
    ]

    return ACMGResult(
        variants=results,
        pathogenic_count=pathogenic,
        likely_pathogenic_count=likely_path,
        vus_count=vus,
        benign_count=benign,
        actionable_variants=actionable,
    )


def _classify_variant(v: Dict[str, Any]) -> VariantResult:
    gene = v.get("gene", "UNKNOWN")
    cdna = v.get("cdna_change", "")
    key = (gene, cdna)

    classification = KNOWN_PATHOGENIC.get(key, _infer_classification(v))
    criteria = _build_criteria(v, classification)
    score = _net_score(criteria)

    return VariantResult(
        variant_id=v.get("variant_id", f"{gene}:{cdna}"),
        gene=gene,
        cdna_change=cdna or "c.?",
        protein_change=v.get("protein_change", "p.?"),
        chromosome=str(v.get("chromosome", "?")),
        position=v.get("position", 0),
        ref=v.get("ref", "N"),
        alt=v.get("alt", "N"),
        zygosity=v.get("zygosity", "Heterozygous"),
        gnomad_af=v.get("gnomad_af", 0.0),
        classification=classification,
        classification_score=score,
        criteria_met=criteria,
        clinical_significance=_significance_text(classification),
        associated_diseases=DISEASE_ASSOCIATIONS.get(gene, ["Unknown"]),
        actionable=classification in (ACMGClassification.PATHOGENIC, ACMGClassification.LIKELY_PATHOGENIC),
        recommendation=_recommendation(classification, gene),
    )


def _infer_classification(v: Dict[str, Any]) -> ACMGClassification:
    af = v.get("gnomad_af", 0.0)
    if af > 0.05:
        return ACMGClassification.BENIGN
    if af > 0.01:
        return ACMGClassification.LIKELY_BENIGN
    if af == 0.0:
        return ACMGClassification.VUS
    return random.choice([ACMGClassification.VUS, ACMGClassification.LIKELY_PATHOGENIC])


def _build_criteria(v: Dict[str, Any], cls: ACMGClassification) -> List[ACMGCriterion]:
    criteria = []
    gene = v.get("gene", "")
    af = v.get("gnomad_af", 0.0)
    cdna = v.get("cdna_change", "")

    is_lof = any(x in cdna for x in ["dup", "del", "ins", "Ter", "fs"])

    if is_lof and gene in ("BRCA1", "FBN1"):
        criteria.append(ACMGCriterion(
            code="PVS1",
            met=True,
            strength="Pathogenic_VeryStrong",
            description="Null variant (frameshift/nonsense) in a gene where LOF is a known disease mechanism.",
        ))

    if cls in (ACMGClassification.PATHOGENIC, ACMGClassification.LIKELY_PATHOGENIC):
        criteria.append(ACMGCriterion(
            code="PS1",
            met=True,
            strength="Pathogenic_Strong",
            description="Same amino acid change as a previously established pathogenic variant (ClinVar).",
        ))

    if af < 0.0001:
        criteria.append(ACMGCriterion(
            code="PM2",
            met=True,
            strength="Pathogenic_Moderate",
            description=f"Absent from gnomAD controls (AF={af:.6f} < 0.0001). Supports pathogenicity.",
        ))

    criteria.append(ACMGCriterion(
        code="PP3",
        met=True,
        strength="Pathogenic_Supporting",
        description="Multiple in-silico predictors (SIFT, PolyPhen-2, CADD>20) indicate deleterious effect.",
    ))

    if af > 0.01:
        criteria.append(ACMGCriterion(
            code="BA1",
            met=True,
            strength="Benign_StandAlone",
            description=f"Allele frequency in gnomAD ({af:.4f}) exceeds 5% threshold — stand-alone benign.",
        ))

    if cls in (ACMGClassification.BENIGN, ACMGClassification.LIKELY_BENIGN):
        criteria.append(ACMGCriterion(
            code="BP4",
            met=True,
            strength="Benign_Supporting",
            description="In-silico tools predict no significant impact on protein function.",
        ))

    return criteria


def _net_score(criteria: List[ACMGCriterion]) -> int:
    weight = {
        "Pathogenic_VeryStrong": 8,
        "Pathogenic_Strong": 4,
        "Pathogenic_Moderate": 2,
        "Pathogenic_Supporting": 1,
        "Benign_StandAlone": -8,
        "Benign_Strong": -4,
        "Benign_Supporting": -1,
    }
    return sum(weight.get(c.strength, 0) for c in criteria if c.met)


def _significance_text(cls: ACMGClassification) -> str:
    return {
        ACMGClassification.PATHOGENIC: "This variant is causative for the associated disease(s).",
        ACMGClassification.LIKELY_PATHOGENIC: "High probability of pathogenicity; clinical action warranted.",
        ACMGClassification.VUS: "Uncertain significance — further segregation or functional studies needed.",
        ACMGClassification.LIKELY_BENIGN: "Likely not clinically significant; routine monitoring.",
        ACMGClassification.BENIGN: "No clinical significance — common population variant.",
    }[cls]


def _recommendation(cls: ACMGClassification, gene: str) -> str:
    if cls == ACMGClassification.PATHOGENIC:
        return f"Initiate disease-specific management protocol for {gene}-related condition. Offer cascade testing to first-degree relatives."
    if cls == ACMGClassification.LIKELY_PATHOGENIC:
        return "Treat as pathogenic in clinical context. Confirm with functional assay if available."
    if cls == ACMGClassification.VUS:
        return "Reclassification expected as more evidence accumulates. Consider functional studies or family segregation analysis."
    return "No immediate action required. Document and re-evaluate if phenotype evolves."
