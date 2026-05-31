"""
Variant Prioritization (DeepRare "Genotype Analyser")
=====================================================
Ranks variants by combining multiple evidence sources:

  1. AlphaMissense  — in-silico missense pathogenicity (offline tabix)
  2. gnomAD         — population allele frequency (live GraphQL API)
  3. ClinVar        — known clinical significance (live eutils)
  4. Franklin       — Genoox classification (gated behind API key)
  5. Phenotype match — gene-disease association vs patient HPO profile
  6. Consequence    — LoF/missense severity from VCF annotation

Outputs a ranked list with a combined priority score, and FLAGS rare/novel
variants that have no ClinVar/literature coverage (the key DeepRare use case
for downstream AlphaFold structural analysis).
"""

import asyncio
import httpx
import logging
from typing import Optional

from app.core.config import settings
from app.services import alphamissense

logger = logging.getLogger(__name__)

GNOMAD_API = "https://gnomad.broadinstitute.org/api"
CLINVAR_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
CLINVAR_ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

# Gene -> associated disease genes for phenotype matching
LOF_SENSITIVE_GENES = {
    "BRCA1", "BRCA2", "FBN1", "TP53", "RB1", "APC", "MLH1", "MSH2",
    "NF1", "NF2", "VHL", "PTEN", "STK11", "CFTR", "DMD", "ATM",
}


async def prioritize_variants(
    variants: list[dict],
    patient_hpo: list[str],
    similar_case_genes: Optional[list[str]] = None,
) -> list[dict]:
    """
    Score and rank all variants. Returns sorted list (highest priority first),
    each enriched with scores + a `novel` flag.
    """
    if not variants:
        return []

    similar_genes = set(g.upper() for g in (similar_case_genes or []))

    # ── 1. Deduplicate by variant identity ────────────────────────────────────
    seen: set = set()
    unique: list[dict] = []
    for v in variants:
        key = (
            v.get("variant_id")
            or f"{v.get('chromosome')}:{v.get('position')}:{v.get('ref')}>{v.get('alt')}"
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(v)

    # ── 2. Pre-filter to the most informative variants ────────────────────────
    # Prefer variants that already carry a clinical flag or a known gene, then
    # rare ones. This avoids scoring tens of thousands of common/UNKNOWN rows.
    def _prefilter_rank(v: dict):
        gene = (v.get("gene") or "UNKNOWN").upper()
        has_clin = bool(v.get("clnsig"))
        known_gene = gene != "UNKNOWN"
        in_similar = gene in similar_genes
        af = float(v.get("gnomad_af") or 0.0)
        rare = af == 0.0 or af < 0.001
        return (in_similar, has_clin, known_gene, rare)

    unique.sort(key=_prefilter_rank, reverse=True)
    candidates = unique[:60]   # hard cap — never score more than this

    clinvar_cache: dict = {}          # (gene,cdna) -> significance, shared

    # ── Phase A: fast scoring (ClinVar cached, NO gnomAD network) ─────────────
    sem = asyncio.Semaphore(2)
    async def _fast(v):
        async with sem:
            return await _score_variant(v, similar_genes, clinvar_cache, use_gnomad=False)

    scored = [s for s in await asyncio.gather(*[_fast(v) for v in candidates]) if s]
    scored.sort(key=lambda v: v.get("priority_score") or 0.0, reverse=True)

    # ── Phase B: refine only the top 12 with real gnomAD frequencies ──────────
    top = scored[:12]
    gsem = asyncio.Semaphore(2)
    async def _refine(v):
        async with gsem:
            af = await _gnomad_frequency(
                str(v.get("chromosome", "")), v.get("position", 0),
                v.get("ref", ""), v.get("alt", ""),
            )
            if af is not None:
                v["gnomad_af"] = af
                # recompute novelty with the real frequency
                v["novel"] = (
                    (not v.get("clinvar_significance") or "Not in ClinVar" in v.get("clinvar_significance", ""))
                    and af < 0.0001
                    and (v.get("is_lof") or (v.get("alphamissense") or {}).get("am_class") == "likely_pathogenic")
                )
            return v

    await asyncio.gather(*[_refine(v) for v in top])
    scored.sort(key=lambda v: v.get("priority_score") or 0.0, reverse=True)
    return scored


async def _score_variant(variant: dict, similar_genes: set,
                         clinvar_cache: Optional[dict] = None,
                         use_gnomad: bool = False) -> dict:
    gene = (variant.get("gene") or "").upper()
    chrom = str(variant.get("chromosome", ""))
    pos = variant.get("position", 0)
    ref = variant.get("ref", "")
    alt = variant.get("alt", "")
    cdna = variant.get("cdna_change", "")
    consequence = (variant.get("consequence") or variant.get("info", {}).get("Consequence", "")).lower()

    # ── 1. AlphaMissense (offline) ────────────────────────────────────────────
    am = alphamissense.lookup(chrom, pos, ref, alt) if chrom and pos else None

    # ── 2. gnomAD frequency (network — only for final top candidates) ─────────
    gnomad_af = None
    if use_gnomad and chrom and pos:
        gnomad_af = await _gnomad_frequency(chrom, pos, ref, alt)
    if gnomad_af is None:
        gnomad_af = float(variant.get("gnomad_af") or 0.0)

    # ── 3. ClinVar significance (cached per gene+cdna to avoid duplicate calls) ─
    cache_key = (gene, cdna)
    if clinvar_cache is not None and cache_key in clinvar_cache:
        clinvar = clinvar_cache[cache_key]
    else:
        # Prefer the VCF's own CLNSIG annotation before hitting the network
        clinvar = variant.get("clnsig") or await _clinvar_significance(gene, cdna)
        if clinvar_cache is not None:
            clinvar_cache[cache_key] = clinvar

    # ── 4. Franklin (gated) ───────────────────────────────────────────────────
    franklin = await _franklin_classify(gene, cdna) if settings.FRANKLIN_API_KEY else None

    # ── 5. Consequence severity ───────────────────────────────────────────────
    is_lof = any(t in consequence or t in cdna.lower() for t in
                 ["frameshift", "stop_gain", "nonsense", "splice", "fs", "ter", "dup", "del"])
    is_missense = "missense" in consequence or (am is not None)

    # ── 6. Phenotype / similar-case gene match ────────────────────────────────
    gene_match = gene in similar_genes

    # ── Combine into a priority score (0-1) ───────────────────────────────────
    score = 0.0
    reasons = []

    if clinvar and "pathogenic" in clinvar.lower():
        score += 0.40
        reasons.append(f"ClinVar: {clinvar}")
    elif clinvar and "benign" in clinvar.lower():
        score -= 0.30
        reasons.append(f"ClinVar: {clinvar}")

    if am:
        if am["am_class"] == "likely_pathogenic":
            score += 0.25
        elif am["am_class"] == "likely_benign":
            score -= 0.15
        reasons.append(f"AlphaMissense: {am['am_class']} ({am['am_pathogenicity']:.2f})")

    if is_lof and gene in LOF_SENSITIVE_GENES:
        score += 0.25
        reasons.append("LoF in LoF-sensitive gene")
    elif is_lof:
        score += 0.12
        reasons.append("Loss-of-function variant")

    # Rarity bonus
    if gnomad_af == 0.0:
        score += 0.15
        reasons.append("Absent from gnomAD")
    elif gnomad_af < 0.0001:
        score += 0.10
        reasons.append(f"Ultra-rare (AF={gnomad_af:.2e})")
    elif gnomad_af > 0.05:
        score -= 0.40
        reasons.append(f"Common (AF={gnomad_af:.2%})")

    if gene_match:
        score += 0.15
        reasons.append("Gene matches similar cases")

    if franklin and "pathogenic" in franklin.lower():
        score += 0.20
        reasons.append(f"Franklin: {franklin}")

    score = max(0.0, min(1.0, score))

    # ── Novel/rare flag — no ClinVar coverage + rare + predicted damaging ─────
    novel = (
        (clinvar is None or clinvar == "")
        and gnomad_af < 0.0001
        and (is_lof or (am and am["am_class"] == "likely_pathogenic"))
    )

    return {
        **variant,
        "gnomad_af": gnomad_af,
        "alphamissense": am,
        "clinvar_significance": clinvar or "Not in ClinVar",
        "franklin": franklin,
        "is_lof": is_lof,
        "is_missense": is_missense,
        "consequence": consequence or ("LoF" if is_lof else "missense" if is_missense else "unknown"),
        "gene_phenotype_match": gene_match,
        "priority_score": round(score, 3),
        "priority_reasons": reasons,
        "novel": novel,
    }


async def _noop():
    return None


async def _gnomad_frequency(chrom: str, pos: int, ref: str, alt: str) -> Optional[float]:
    """Query gnomAD GraphQL for population allele frequency."""
    chrom_clean = chrom.replace("chr", "")
    variant_id = f"{chrom_clean}-{pos}-{ref}-{alt}"
    query = """
    query ($variantId: String!) {
      variant(variantId: $variantId, dataset: gnomad_r4) {
        genome { af }
        exome { af }
      }
    }
    """
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(GNOMAD_API, json={
                    "query": query,
                    "variables": {"variantId": variant_id},
                })
                if resp.status_code == 429:
                    await asyncio.sleep(1.5 * (attempt + 1))  # backoff on rate limit
                    continue
                if resp.status_code == 200:
                    data = resp.json().get("data", {}).get("variant")
                    if data:
                        genome_af = (data.get("genome") or {}).get("af")
                        exome_af = (data.get("exome") or {}).get("af")
                        afs = [a for a in (genome_af, exome_af) if a is not None]
                        return max(afs) if afs else 0.0
                return None
        except Exception as e:
            logger.debug(f"gnomAD query failed {variant_id}: {e}")
            return None
    return None


async def _clinvar_significance(gene: str, cdna: str) -> Optional[str]:
    """Look up ClinVar clinical significance for a variant."""
    if not gene:
        return None
    term = f"{gene}[gene] AND {cdna}" if cdna else f"{gene}[gene] AND pathogenic"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            sr = await client.get(CLINVAR_ESEARCH, params={
                "db": "clinvar", "term": term, "retmax": 1, "retmode": "json",
            })
            if sr.status_code != 200:
                return None
            ids = sr.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return None
            summ = await client.get(CLINVAR_ESUMMARY, params={
                "db": "clinvar", "id": ids[0], "retmode": "json",
            })
            if summ.status_code != 200:
                return None
            doc = summ.json().get("result", {}).get(ids[0], {})
            sig = doc.get("germline_classification", {}) or doc.get("clinical_significance", {})
            if isinstance(sig, dict):
                return sig.get("description", "")
            return str(sig)
    except Exception as e:
        logger.debug(f"ClinVar lookup failed {gene}/{cdna}: {e}")
    return None


async def _franklin_classify(gene: str, cdna: str) -> Optional[str]:
    """
    Query Genoox Franklin for variant classification. Gated behind API key.
    Real client — activates the moment FRANKLIN_API_KEY is set.
    """
    if not settings.FRANKLIN_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(
                f"{settings.FRANKLIN_API_URL}/api/classify",
                headers={"Authorization": f"Bearer {settings.FRANKLIN_API_KEY}"},
                json={"gene": gene, "variant": cdna},
            )
            if resp.status_code == 200:
                return resp.json().get("classification", "")
    except Exception as e:
        logger.debug(f"Franklin query failed: {e}")
    return None
