"""
Celery application — job queue for long-running work:
  - nf-core pipeline runs (FASTQ/BAM -> VCF)
  - pipeline installation (nextflow pull)
  - RareBench indexing into Qdrant
  - variant scoring, structure analysis

Progress is published to Redis pub/sub so the API can stream it via SSE.
"""

from celery import Celery
from app.core.config import settings

celery = Celery(
    "raredx",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=60 * 60 * 24 * 7,  # keep results 1 week
    task_routes={
        "app.tasks.pipeline_tasks.*": {"queue": "pipelines"},
        "app.tasks.indexing_tasks.*": {"queue": "indexing"},
        "app.tasks.scoring_tasks.*": {"queue": "scoring"},
    },
)

# Import all ORM models up front so SQLAlchemy's mapper registry is complete
# in the worker process (prevents 'failed to locate name User' mapper errors).
import app.models.db  # noqa: E402,F401

# Ensure task modules are imported so Celery registers them
celery.autodiscover_tasks(["app.tasks"])

# Explicit imports (autodiscover can miss in some layouts)
import app.tasks.pipeline_tasks  # noqa: E402,F401
import app.tasks.indexing_tasks  # noqa: E402,F401
