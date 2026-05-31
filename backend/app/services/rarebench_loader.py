"""
RareBench Loader
================
Downloads the public RareBench dataset (chenxz/RareBench on HuggingFace) and
converts each case into the {hpo_ids, hpo_names, disease} profile used for
Qdrant indexing.

RareBench subsets: RAMEDIS, MME, HMS, LIRICAL — each case is a list of HPO IDs
plus a ground-truth disease label (OMIM/ORPHA).
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

SUBSETS = ["RAMEDIS", "MME", "HMS", "LIRICAL"]


def load_rarebench() -> list[dict]:
    """
    Load RareBench cases. Returns list of:
      {id, hpo_ids: [...], hpo_names: [...], disease, source, omim_id}
    Requires `datasets` and network access on first run (cached afterward).
    """
    try:
        from datasets import load_dataset
    except ImportError:
        logger.error("`datasets` not installed — cannot load RareBench")
        return []

    all_cases: list[dict] = []

    for subset in SUBSETS:
        try:
            logger.info(f"Loading RareBench subset: {subset}")
            ds = load_dataset("chenxz/RareBench", subset, split="test")
        except Exception as e:
            logger.warning(f"Could not load RareBench/{subset}: {e}")
            continue

        for i, row in enumerate(ds):
            case = _parse_row(row, subset, i)
            if case:
                all_cases.append(case)

    logger.info(f"Loaded {len(all_cases)} RareBench cases total")
    return all_cases


def _parse_row(row: dict, subset: str, idx: int) -> Optional[dict]:
    """
    RareBench rows vary by subset. Common fields:
      - 'Phenotype' : list of HPO IDs (or comma string)
      - 'RareDisease': disease label / OMIM id
    """
    # Phenotype HPO IDs
    pheno = row.get("Phenotype") or row.get("phenotype") or row.get("HPO") or []
    if isinstance(pheno, str):
        hpo_ids = [p.strip() for p in pheno.replace(";", ",").split(",") if p.strip()]
    elif isinstance(pheno, list):
        hpo_ids = [str(p).strip() for p in pheno if str(p).strip()]
    else:
        hpo_ids = []

    hpo_ids = [h for h in hpo_ids if h.upper().startswith("HP")]
    if not hpo_ids:
        return None

    # Disease label
    disease = (
        row.get("RareDisease") or row.get("Disease") or
        row.get("disease") or row.get("Label") or ""
    )
    if isinstance(disease, list):
        disease = disease[0] if disease else ""
    disease = str(disease).strip()

    omim_id = ""
    if "OMIM" in disease.upper():
        import re
        m = re.search(r"(\d{6})", disease)
        if m:
            omim_id = m.group(1)

    # Resolve HPO names from the ontology (best-effort)
    hpo_names = _resolve_names(hpo_ids)

    return {
        "id": f"rb-{subset}-{idx}",
        "hpo_ids": hpo_ids,
        "hpo_names": hpo_names,
        "disease": disease or f"{subset} case {idx}",
        "source": f"RareBench/{subset}",
        "omim_id": omim_id,
    }


def _resolve_names(hpo_ids: list[str]) -> list[str]:
    """Map HPO IDs to names using the loaded ontology; fall back to the ID."""
    try:
        from app.services.hpo_ontology import get_hpo_term, is_ready
        if is_ready():
            names = []
            for hid in hpo_ids:
                term = get_hpo_term(hid)
                names.append(term["name"] if term else hid)
            return names
    except Exception:
        pass
    return hpo_ids
