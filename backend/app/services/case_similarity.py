"""
Case Similarity Service (DeepRare "Case Searcher")
==================================================
Embeds known rare-disease cases into Qdrant and retrieves the most similar
historical cases for a new patient by their HPO phenotype profile.

Corpus: RareBench (chenxz/RareBench on HuggingFace) — MME, HMS, LIRICAL, RAMEDIS.
Each case is represented by the names of its HPO terms, embedded with BioLORD.

Also indexes the platform's own completed cases so the DB grows over time.
"""

import logging
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter,
)

from app.core.config import settings
from app.services.embedding_service import embed, get_model

logger = logging.getLogger(__name__)

COLLECTION = "rare_cases"
_client: Optional[QdrantClient] = None
_vector_size: Optional[int] = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.QDRANT_URL, timeout=30)
    return _client


def _ensure_collection():
    global _vector_size
    client = get_client()
    if _vector_size is None:
        # Probe model dimension once
        dim = get_model().get_sentence_embedding_dimension()
        _vector_size = dim
    try:
        client.get_collection(COLLECTION)
    except Exception:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=_vector_size, distance=Distance.COSINE),
        )
        logger.info(f"Created Qdrant collection '{COLLECTION}' (dim={_vector_size})")


def _profile_text(hpo_names: list[str]) -> str:
    """Build the text representation of a case's phenotype profile."""
    return "; ".join(hpo_names)


def index_cases(cases: list[dict], batch_size: int = 256, progress_cb=None) -> int:
    """
    Index a list of cases into Qdrant.
    Each case: {id, hpo_names: [...], hpo_ids: [...], disease, source}
    Returns number indexed.
    """
    _ensure_collection()
    client = get_client()

    total = len(cases)
    indexed = 0
    for start in range(0, total, batch_size):
        batch = cases[start: start + batch_size]
        texts = [_profile_text(c.get("hpo_names", [])) for c in batch]
        # Skip empty profiles
        valid = [(c, t) for c, t in zip(batch, texts) if t.strip()]
        if not valid:
            continue
        vectors = embed([t for _, t in valid])

        points = []
        for (case, _), vec in zip(valid, vectors):
            points.append(PointStruct(
                id=case["id"],
                vector=vec.tolist(),
                payload={
                    "disease": case.get("disease", ""),
                    "hpo_ids": case.get("hpo_ids", []),
                    "hpo_names": case.get("hpo_names", []),
                    "source": case.get("source", "unknown"),
                    "orpha_code": case.get("orpha_code", ""),
                    "omim_id": case.get("omim_id", ""),
                    "gene": case.get("gene", ""),
                },
            ))
        client.upsert(collection_name=COLLECTION, points=points)
        indexed += len(points)
        if progress_cb:
            progress_cb(int(100 * indexed / total), f"Indexed {indexed}/{total} cases")

    logger.info(f"Indexed {indexed} cases into Qdrant")
    return indexed


def search_similar(hpo_names: list[str], k: int = 5,
                   source_filter: Optional[str] = None) -> list[dict]:
    """
    Find the top-k most similar historical cases for a patient HPO profile.
    Returns [{disease, score, source, hpo_overlap, gene, orpha_code, omim_id}]
    """
    if not hpo_names:
        return []
    try:
        _ensure_collection()
        client = get_client()
        query_vec = embed([_profile_text(hpo_names)])[0]

        qfilter = None
        if source_filter:
            from qdrant_client.models import FieldCondition, MatchValue
            qfilter = Filter(must=[
                FieldCondition(key="source", match=MatchValue(value=source_filter))
            ])

        hits = client.search(
            collection_name=COLLECTION,
            query_vector=query_vec.tolist(),
            limit=k,
            query_filter=qfilter,
        )

        patient_set = set(n.lower() for n in hpo_names)
        results = []
        for h in hits:
            payload = h.payload or {}
            case_hpo = set(n.lower() for n in payload.get("hpo_names", []))
            overlap = list(patient_set & case_hpo)
            results.append({
                "disease": payload.get("disease", "Unknown"),
                "score": round(float(h.score), 4),
                "source": payload.get("source", ""),
                "gene": payload.get("gene", ""),
                "orpha_code": payload.get("orpha_code", ""),
                "omim_id": payload.get("omim_id", ""),
                "hpo_overlap": overlap[:6],
                "overlap_count": len(overlap),
            })
        return results
    except Exception as e:
        logger.warning(f"Case similarity search failed: {e}")
        return []


def collection_stats() -> dict:
    try:
        client = get_client()
        info = client.get_collection(COLLECTION)
        return {
            "exists": True,
            "count": info.points_count,
            "vector_size": _vector_size,
        }
    except Exception:
        return {"exists": False, "count": 0}
