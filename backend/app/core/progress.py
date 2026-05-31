"""
Progress pub/sub over Redis.
Celery tasks publish stage/progress events; the API subscribes and streams
them to the browser via SSE.
"""

import json
import logging
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

_redis = None


def _client():
    global _redis
    if _redis is None:
        _redis = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


def channel(case_id: str) -> str:
    return f"case:progress:{case_id}"


def publish(case_id: str, stage: str, status: str, progress: int,
            message: str, data: dict | None = None):
    """Publish a progress event for a case."""
    event = {
        "stage": stage,
        "status": status,
        "progress": progress,
        "message": message,
        "data": data or {},
    }
    try:
        c = _client()
        c.publish(channel(case_id), json.dumps(event))
        # Also store last event so late subscribers get current state
        c.setex(f"case:laststate:{case_id}", 3600, json.dumps(event))
    except Exception as e:
        logger.debug(f"progress publish failed: {e}")


def get_last_state(case_id: str) -> dict | None:
    try:
        raw = _client().get(f"case:laststate:{case_id}")
        return json.loads(raw) if raw else None
    except Exception:
        return None
