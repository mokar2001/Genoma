"""
Celery tasks for building the Qdrant case-similarity index.
"""

import logging
from app.core.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.indexing_tasks.index_rarebench", bind=True)
def index_rarebench(self):
    """Download RareBench and index all cases into Qdrant. Run once at setup."""
    from app.services.rarebench_loader import load_rarebench
    from app.services.case_similarity import index_cases, collection_stats

    def progress(pct, msg):
        self.update_state(state="PROGRESS", meta={"progress": pct, "message": msg})
        logger.info(f"[index_rarebench] {pct}% {msg}")

    # Skip if already populated
    stats = collection_stats()
    if stats.get("count", 0) > 100:
        return {"status": "already_indexed", "count": stats["count"]}

    progress(5, "Downloading RareBench dataset…")
    cases = load_rarebench()
    if not cases:
        return {"status": "no_cases", "count": 0}

    progress(20, f"Embedding and indexing {len(cases)} cases…")
    n = index_cases(cases, progress_cb=lambda p, m: progress(20 + int(p * 0.8), m))

    return {"status": "complete", "count": n}


@celery.task(name="app.tasks.indexing_tasks.index_own_case")
def index_own_case(case_profile: dict):
    """Index a completed platform case so future searches can find it."""
    from app.services.case_similarity import index_cases
    try:
        index_cases([case_profile])
        return {"status": "indexed", "id": case_profile.get("id")}
    except Exception as e:
        logger.warning(f"Failed to index own case: {e}")
        return {"status": "failed", "error": str(e)}
