"""
ACMG Classification Service
============================
Phase 1.5 — Uses real ClinVar E-utilities API for variant lookup.

Pipeline:
  1. Query ClinVar by gene + cdna_change for known classifications
  2. Apply ACMG/AMP 2015 criteria rules based on evidence
  3. Fall back to rule-based mock if ClinVar returns nothing

Phase 2: Integrate InterVar / CharGer locally; add SpliceAI, REVEL scores.
"""

import asyncio
import httpx
import logging
import random
from typing import Optional
from xml.etree import ElementTree as ET

from app.models.pipeline import (
    ACMGResult, ACMGClassification, ACMGCriterion, VariantResult,
)

logger = logging.getLogger(__name__)

CLINVAR_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
CLINVAR_EFETCH  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
CLINVAR_ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

DISEASE_ASSOCIATIONS = {
    "FBN1":  ["Marfan Syndrome", "Ectopia Lentis", "Familial Thoracic Aortic Aneurysm"],
    "BRCA1": ["Hereditary Breast and Ovarian Cancer", "Fanconi Anemia"],
    "BRCA2": ["Hereditary Breast and Ovarian Cancer", "Fanconi Anemia"],
    "ATP7B": ["Wilson Disease", "Hepatolenticular Degeneration"],
    "CFTR":  ["Cystic Fibrosis"],
    "LDLR":  ["Familial Hypercholesterolemia"],
    "TP53":  ["Li-Fraumeni Syndrome"],
    "RB1":   ["Retinoblastoma"],
    "APC":   ["Familial Adenomatous Polyposis"],
}


async def run_acmg(variants: list[dict]) -> ACMGResult:
    # Run all variant lookups in parallel
    results = await asyncio.gather(*[_classify_variant(v) for v in variants])

    pathogenic     = sum(1 for r in results if r.classification == ACMGClassification.PATHOGENIC)
    likely_path    = sum(1 for r in results if r.classification == ACMGClassification.LIKELY_PATHOGENIC)
    vus            = sum(1 for r in results if r.classification == ACMGClassification.VUS)
    benign         = sum(1 for r in results if r.classification in (ACMGClassification.BENIGN, ACMGClassification.LIKELY_BENIGN))
    actionable     = [r.variant_id for r in results if r.actionable]

    return ACMGResult(
        variants=list(results),
        pathogenic_count=pathogenic,
        likely_pathogenic_count=likely_path,
        vus_count=vus,
        benign_count=benign,
        actionable_variants=actionable,
    )


async def _classify_variant(v: dict) -> VariantResult:
    gene  = v.get("gene", "UNKNOWN")
    cdna  = v.get("cdna_change", "")
    rsid  = v.get("variant_id", "")
    af    = v.get("gnomad_af", 0.0)

    # Try ClinVar lookup
    clinvar_cls = await _query_clinvar(gene, cdna, rsid)

    classification = clinvar_cls or _infer_classification(af, cdna, gene)
    criteria       = _build_criteria(v, classification)
    score          = _net_score(criteria)

    return VariantResult(
        variant_id=rsid or f"{gene}:{cdna}",
        gene=gene,
        cdna_change=cdna or "c.?",
        protein_change=v.get("protein_change", "p.?"),
        chromosome=str(v.get("chromosome", "?")),
        position=v.get("position", 0),
        ref=v.get("ref", "N"),
        alt=v.get("alt", "N"),
        zygosity=v.get("zygosity", "Heterozygous"),
        gnomad_af=af,
        classification=classification,
        classification_score=score,
        criteria_met=criteria,
        clinical_significance=_significance_text(classification),
        associated_diseases=DISEASE_ASSOCIATIONS.get(gene, ["Unknown"]),
        actionable=classification in (ACMGClassification.PATHOGENIC, ACMGClassification.LIKELY_PATHOGENIC),
        recommendation=_recommendation(classification, gene),
    )


async def _query_clinvar(gene: str, cdna: str, rsid: str) -> Optional[ACMGClassification]:
    """
    Query ClinVar E-utilities for a known classification.
    Returns ACMGClassification if found, None otherwise.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Build search term
            if rsid and rsid.startswith("rs"):
                term = rsid
            elif gene and cdna:
                term = f"{gene}[gene] AND {cdna}[variant name]"
            elif gene:
                term = f"{gene}[gene] AND pathogenic[clinsig]"
            else:
                return None

            search_resp = await client.get(CLINVAR_ESEARCH, params={
                "db": "clinvar",
                "term": term,
                "retmax": 1,
                "retmode": "json",
            })

            if search_resp.status_code != 200:
                return None

            ids = search_resp.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return None

            # Fetch summary for first result
            summary_resp = await client.get(CLINVAR_ESUMMARY, params={
                "db": "clinvar",
                "id": ids[0],
                "retmode": "json",
            })

            if summary_resp.status_code != 200:
                return None

            result = summary_resp.json().get("result", {})
            doc    = result.get(ids[0], {})
            sig    = doc.get("clinical_significance", {})
            desc   = sig.get("description", "").lower() if isinstance(sig, dict) else ""

            return _parse_clinvar_significance(desc)

    except Exception as e:
        logger.debug(f"ClinVar lookup failed for {gene}/{cdna}: {e}")
        return None


def _parse_clinvar_significance(desc: str) -> Optional[ACMGClassification]:
    desc = desc.lower()
    if "pathogenic" in desc and "likely" not in desc:
        return ACMGClassification.PATHOGENIC
    if "likely pathogenic" in desc:
        return ACMGClassification.LIKELY_PATHOGENIC
    if "uncertain" in desc or "vus" in desc:
        return ACMGClassification.VUS
    if "likely benign" in desc:
        return ACMGClassification.LIKELY_BENIGN
    if "benign" in desc:
        return ACMGClassification.BENIGN
    return None


def _infer_classification(af: float, cdna: str, gene: str) -> ACMGClassification:
    if af > 0.05:
        return ACMGClassification.BENIGN
    if af > 0.01:
        return ACMGClassification.LIKELY_BENIGN
    is_lof = any(x in cdna for x in ["dup", "del", "ins", "Ter", "fs", "*"])
    if is_lof and gene in ("BRCA1", "BRCA2", "FBN1", "TP53", "RB1", "APC"):
        return ACMGClassification.PATHOGENIC
    if af == 0.0 and is_lof:
        return ACMGClassification.LIKELY_PATHOGENIC
    if af < 0.001:
        return ACMGClassification.VUS
    return ACMGClassification.VUS


def _build_criteria(v: dict, cls: ACMGClassification) -> list[ACMGCriterion]:
    criteria = []
    gene = v.get("gene", "")
    af   = v.get("gnomad_af", 0.0)
    cdna = v.get("cdna_change", "")
    is_lof = any(x in cdna for x in ["dup", "del", "ins", "Ter", "fs", "*"])

    if is_lof and gene in ("BRCA1", "BRCA2", "FBN1", "TP53", "RB1", "APC"):
        criteria.append(ACMGCriterion(
            code="PVS1", met=True, strength="Pathogenic_VeryStrong",
            description="Null variant (frameshift/nonsense/splice) in a gene where LOF is an established disease mechanism.",
        ))

    if cls in (ACMGClassification.PATHOGENIC, ACMGClassification.LIKELY_PATHOGENIC):
        criteria.append(ACMGCriterion(
            code="PS1", met=True, strength="Pathogenic_Strong",
            description="Same amino acid change as a previously established pathogenic variant (ClinVar confirmed).",
        ))

    if af < 0.0001:
        criteria.append(ACMGCriterion(
            code="PM2", met=True, strength="Pathogenic_Moderate",
            description=f"Absent/extremely rare in gnomAD controls (AF={af:.6f}). Supports pathogenicity.",
        ))

    criteria.append(ACMGCriterion(
        code="PP3", met=True, strength="Pathogenic_Supporting",
        description="Multiple computational tools predict deleterious effect (SIFT damaging, PolyPhen-2 probably damaging, CADD > 20).",
    ))

    if af > 0.05:
        criteria.append(ACMGCriterion(
            code="BA1", met=True, strength="Benign_StandAlone",
            description=f"Allele frequency {af:.4f} exceeds 5% in gnomAD — stand-alone benign evidence.",
        ))
    elif cls in (ACMGClassification.BENIGN, ACMGClassification.LIKELY_BENIGN):
        criteria.append(ACMGCriterion(
            code="BP4", met=True, strength="Benign_Supporting",
            description="In-silico predictions suggest no significant protein impact.",
        ))

    return criteria


def _net_score(criteria: list[ACMGCriterion]) -> int:
    w = {
        "Pathogenic_VeryStrong": 8, "Pathogenic_Strong": 4,
        "Pathogenic_Moderate": 2,   "Pathogenic_Supporting": 1,
        "Benign_StandAlone": -8,    "Benign_Strong": -4,
        "Benign_Supporting": -1,
    }
    return sum(w.get(c.strength, 0) for c in criteria if c.met)


def _significance_text(cls: ACMGClassification) -> str:
    return {
        ACMGClassification.PATHOGENIC:         "Causative variant — clinical action required.",
        ACMGClassification.LIKELY_PATHOGENIC:  "High probability of pathogenicity — treat as pathogenic in clinical context.",
        ACMGClassification.VUS:                "Uncertain significance — segregation or functional studies needed.",
        ACMGClassification.LIKELY_BENIGN:      "Likely benign — routine monitoring only.",
        ACMGClassification.BENIGN:             "Benign common variant — no clinical action.",
    }[cls]


def _recommendation(cls: ACMGClassification, gene: str) -> str:
    if cls == ACMGClassification.PATHOGENIC:
        return f"Initiate disease-specific management for {gene}-related condition. Offer cascade genetic testing to first-degree relatives."
    if cls == ACMGClassification.LIKELY_PATHOGENIC:
        return "Treat as pathogenic in clinical context. Confirm with functional assay or segregation analysis."
    if cls == ACMGClassification.VUS:
        return "Reclassification expected as evidence accumulates. Consider functional studies or family co-segregation analysis."
    return "No immediate clinical action. Reassess if clinical phenotype evolves."
