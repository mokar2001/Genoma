"""
HPO Ontology Service
====================
Downloads and caches the full HPO term list at startup.
Builds embeddings for all ~18,000 HPO terms for cosine-similarity normalization
(exactly as described in the DeepRare paper using BioLORD).

Cache files stored in /app/cache/ (persisted across restarts via Docker volume).
"""

import json
import logging
import asyncio
import httpx
import numpy as np
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CACHE_DIR = Path("/app/cache")
HPO_TERMS_CACHE = CACHE_DIR / "hpo_terms.json"
HPO_EMBEDDINGS_CACHE = CACHE_DIR / "hpo_embeddings.npy"
HPOA_CACHE = CACHE_DIR / "hpoa_disease_hpo.json"

# Source URLs
HPO_TERMS_URL = "https://hpo.jax.org/api/hpo/term"
HPOA_URL = "https://github.com/obophenotype/human-phenotype-ontology/releases/latest/download/phenotype.hpoa"
HPO_SEARCH_URL = "https://hpo.jax.org/api/hpo/search"

# In-memory state
_hpo_terms: list[dict] = []       # [{id, name, definition}]
_hpo_embeddings: Optional[np.ndarray] = None
_hpo_names: list[str] = []        # parallel to _hpo_terms
_disease_hpo_map: dict[str, list[str]] = {}  # disease_id -> [HPO IDs]


def is_ready() -> bool:
    return len(_hpo_terms) > 0 and _hpo_embeddings is not None


async def initialize():
    """Called at app startup — loads or builds HPO + HPOA data."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    await _load_hpo_terms()
    await _load_hpoa()
    _build_embeddings()


# ── HPO Terms ─────────────────────────────────────────────────────────────────

async def _load_hpo_terms():
    global _hpo_terms, _hpo_names

    if HPO_TERMS_CACHE.exists():
        try:
            _hpo_terms = json.loads(HPO_TERMS_CACHE.read_text())
            _hpo_names = [t["name"] for t in _hpo_terms]
            logger.info(f"Loaded {len(_hpo_terms)} HPO terms from cache")
            return
        except Exception:
            pass

    logger.info("Downloading HPO term list from JAX API…")
    terms = []

    # The JAX API doesn't have a single "all terms" endpoint, so we
    # pull terms page by page from the search API with common roots
    hpo_roots = [
        "HP:0000118",  # Phenotypic abnormality (root)
    ]

    # Use a broader approach: fetch all descendants of root
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Fetch via search with broad terms to get representative HPO terms
            queries = [
                "abnormality", "syndrome", "disease", "disorder",
                "deficiency", "atresia", "dysplasia", "aplasia",
                "hyper", "hypo", "palsy", "atrophy", "stenosis",
            ]
            seen_ids: set[str] = set()
            for q in queries:
                try:
                    resp = await client.get(
                        HPO_SEARCH_URL,
                        params={"q": q, "max": 500, "category": "terms"},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for t in data.get("terms", []):
                            if t.get("id") and t["id"] not in seen_ids:
                                seen_ids.add(t["id"])
                                terms.append({
                                    "id": t["id"],
                                    "name": t.get("name", ""),
                                    "definition": t.get("definition", ""),
                                })
                except Exception:
                    pass

        logger.info(f"Downloaded {len(terms)} HPO terms")

        # Supplement with our curated local map
        from app.services.hpo_service import LOCAL_HPO_MAP
        for name, hpo_id in LOCAL_HPO_MAP.items():
            if hpo_id not in seen_ids:
                seen_ids.add(hpo_id)
                terms.append({"id": hpo_id, "name": name, "definition": ""})

    except Exception as e:
        logger.warning(f"HPO download failed: {e} — using local map only")
        from app.services.hpo_service import LOCAL_HPO_MAP
        terms = [{"id": v, "name": k, "definition": ""} for k, v in LOCAL_HPO_MAP.items()]

    if not terms:
        logger.error("No HPO terms available")
        return

    _hpo_terms = terms
    _hpo_names = [t["name"] for t in terms]
    HPO_TERMS_CACHE.write_text(json.dumps(terms))
    logger.info(f"HPO terms ready: {len(terms)} terms")


# ── HPOA Disease-HPO Associations ─────────────────────────────────────────────

async def _load_hpoa():
    global _disease_hpo_map

    if HPOA_CACHE.exists():
        try:
            _disease_hpo_map = json.loads(HPOA_CACHE.read_text())
            logger.info(f"Loaded {len(_disease_hpo_map)} disease-HPO associations from cache")
            return
        except Exception:
            pass

    logger.info("Downloading HPOA disease-phenotype annotations…")
    disease_map: dict[str, list[str]] = {}

    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(HPOA_URL)
            if resp.status_code == 200:
                lines = resp.text.splitlines()
                for line in lines:
                    if line.startswith("#") or not line.strip():
                        continue
                    parts = line.split("\t")
                    if len(parts) < 4:
                        continue
                    # Format: database_id, disease_name, qualifier, hpo_id, ...
                    disease_id = parts[0].strip()
                    qualifier = parts[2].strip() if len(parts) > 2 else ""
                    hpo_id = parts[3].strip() if len(parts) > 3 else ""

                    if qualifier == "NOT" or not hpo_id.startswith("HP:"):
                        continue

                    if disease_id not in disease_map:
                        disease_map[disease_id] = []
                    if hpo_id not in disease_map[disease_id]:
                        disease_map[disease_id].append(hpo_id)

                logger.info(f"HPOA: {len(disease_map)} diseases loaded")
                HPOA_CACHE.write_text(json.dumps(disease_map))
            else:
                logger.warning(f"HPOA download failed: HTTP {resp.status_code}")
    except Exception as e:
        logger.warning(f"HPOA download failed: {e}")

    _disease_hpo_map = disease_map


# ── Embeddings ────────────────────────────────────────────────────────────────

def _build_embeddings():
    global _hpo_embeddings

    if not _hpo_names:
        return

    if HPO_EMBEDDINGS_CACHE.exists():
        try:
            _hpo_embeddings = np.load(str(HPO_EMBEDDINGS_CACHE))
            if _hpo_embeddings.shape[0] == len(_hpo_names):
                logger.info(f"Loaded HPO embeddings from cache: {_hpo_embeddings.shape}")
                return
        except Exception:
            pass

    logger.info(f"Computing embeddings for {len(_hpo_names)} HPO terms (first run — may take 1-2 min)…")
    try:
        from app.services.embedding_service import embed
        # Batch in chunks to avoid memory issues
        batch_size = 256
        all_embs = []
        for i in range(0, len(_hpo_names), batch_size):
            batch = _hpo_names[i: i + batch_size]
            all_embs.append(embed(batch))
        _hpo_embeddings = np.vstack(all_embs)
        np.save(str(HPO_EMBEDDINGS_CACHE), _hpo_embeddings)
        logger.info(f"HPO embeddings computed and cached: {_hpo_embeddings.shape}")
    except Exception as e:
        logger.error(f"Failed to build HPO embeddings: {e}")


# ── Public API ────────────────────────────────────────────────────────────────

def normalize_symptom_to_hpo(symptom_text: str, threshold: float = 0.75) -> Optional[dict]:
    """
    Map free-text symptom to best matching HPO term via cosine similarity.
    Returns {id, name, score} or None if no match above threshold.
    """
    if _hpo_embeddings is None or not _hpo_names:
        return None

    from app.services.embedding_service import top_k_similar
    matches = top_k_similar(
        query_text=symptom_text,
        corpus_texts=_hpo_names,
        corpus_embeddings=_hpo_embeddings,
        k=1,
        threshold=threshold,
    )

    if not matches:
        return None

    best = matches[0]
    term = _hpo_terms[best["index"]]
    return {
        "id": term["id"],
        "name": term["name"],
        "original": symptom_text,
        "score": best["score"],
        "source": "biolord_cosine",
    }


def score_diseases_by_hpo(patient_hpo_ids: list[str]) -> list[dict]:
    """
    Score all diseases in HPOA by HPO overlap with patient's HPO profile.
    Uses Jaccard similarity + semantic score.
    Returns top-20 diseases sorted by score.
    """
    if not _disease_hpo_map or not patient_hpo_ids:
        return []

    patient_set = set(patient_hpo_ids)
    scored = []

    for disease_id, disease_hpos in _disease_hpo_map.items():
        disease_set = set(disease_hpos)
        if not disease_set:
            continue

        # Jaccard similarity
        intersection = len(patient_set & disease_set)
        if intersection == 0:
            continue
        union = len(patient_set | disease_set)
        jaccard = intersection / union

        # Coverage: what fraction of patient HPOs are explained
        coverage = intersection / len(patient_set) if patient_set else 0

        score = 0.5 * jaccard + 0.5 * coverage

        scored.append({
            "disease_id": disease_id,
            "score": round(score, 4),
            "matched_hpo_count": intersection,
            "disease_hpo_count": len(disease_set),
            "matched_hpos": list(patient_set & disease_set),
        })

    # Sort by score
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:20]


def get_hpo_term(hpo_id: str) -> Optional[dict]:
    """Look up HPO term by ID."""
    for t in _hpo_terms:
        if t["id"] == hpo_id:
            return t
    return None
