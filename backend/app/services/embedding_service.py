"""
Embedding Service
=================
Loads BioLORD-2023-C (the exact model used in the DeepRare paper).
Falls back to all-MiniLM-L6-v2 if BioLORD can't be loaded.

Used for:
- HPO term normalization (symptom text → HPO ID via cosine similarity)
- Disease name normalization (free text → Orphanet/OMIM ID)
- Case similarity search (patient HPO profile vs disease HPO profiles)
"""

import numpy as np
import logging
import asyncio
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_model = None
_model_name: str = ""

PREFERRED_MODELS = [
    "FremyCompany/BioLORD-2023-C",   # Paper's exact model — best biomedical similarity
    "all-MiniLM-L6-v2",              # Lightweight fallback ~90MB
]


def get_model():
    global _model, _model_name
    if _model is not None:
        return _model

    from sentence_transformers import SentenceTransformer

    for name in PREFERRED_MODELS:
        try:
            logger.info(f"Loading embedding model: {name}")
            _model = SentenceTransformer(name)
            _model_name = name
            logger.info(f"Embedding model loaded: {name}")
            return _model
        except Exception as e:
            logger.warning(f"Could not load {name}: {e}")

    raise RuntimeError("No embedding model could be loaded")


def embed(texts: list[str]) -> np.ndarray:
    """Embed a list of texts. Returns normalized L2 embeddings shape (N, D)."""
    model = get_model()
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=False)


def cosine_similarity_matrix(query: np.ndarray, corpus: np.ndarray) -> np.ndarray:
    """
    Compute cosine similarity between query embeddings and corpus embeddings.
    Since vectors are L2-normalized, dot product == cosine similarity.
    query:  (Q, D)
    corpus: (N, D)
    returns (Q, N)
    """
    return query @ corpus.T


def top_k_similar(
    query_text: str,
    corpus_texts: list[str],
    corpus_embeddings: np.ndarray,
    k: int = 5,
    threshold: float = 0.75,
) -> list[dict]:
    """
    Find top-k most similar corpus items to the query text.
    Returns list of {text, score, index} sorted by score descending.
    threshold: minimum cosine similarity (paper uses 0.8, we use 0.75 to be slightly more permissive)
    """
    q_emb = embed([query_text])  # (1, D)
    scores = cosine_similarity_matrix(q_emb, corpus_embeddings)[0]  # (N,)

    top_indices = np.argsort(scores)[::-1][:k]
    results = []
    for idx in top_indices:
        score = float(scores[idx])
        if score >= threshold:
            results.append({
                "text": corpus_texts[idx],
                "score": score,
                "index": int(idx),
            })
    return results
