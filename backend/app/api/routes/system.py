"""
System / admin routes — index status, trigger RareBench indexing, resource flags.
"""

import os
import logging
from fastapi import APIRouter

from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status")
def system_status():
    from app.services.case_similarity import collection_stats
    stats = collection_stats()
    return {
        "version": settings.APP_VERSION,
        "mock_mode": settings.MOCK_MODE,
        "case_index": {
            "exists": stats.get("exists", False),
            "count": stats.get("count", 0),
        },
        "alphamissense": os.path.exists(settings.ALPHAMISSENSE_TSV),
        "franklin": bool(settings.FRANKLIN_API_KEY),
        "llm": bool(settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY),
    }


@router.post("/index-cases")
def index_cases():
    """Trigger RareBench download + Qdrant indexing in the worker."""
    from app.tasks.indexing_tasks import index_rarebench
    task = index_rarebench.delay()
    return {"job_id": task.id, "status": "indexing_started"}


@router.get("/index-cases/{task_id}")
def index_status(task_id: str):
    from app.core.celery_app import celery
    res = celery.AsyncResult(task_id)
    info = res.info if isinstance(res.info, dict) else {}
    return {
        "state": res.state,
        "progress": info.get("progress", 0),
        "message": info.get("message", ""),
        "result": res.result if res.successful() else None,
    }
