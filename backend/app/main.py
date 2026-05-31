from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import create_tables
from app.api.routes import pipeline, report, demo, auth, cases, proxy, pipelines, system

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AI-powered rare disease diagnostic pipeline — DeepRare implementation "
        "(Nature 2026). 3-tier agentic architecture with LLM synthesis."
    ),
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# NOTE: GZipMiddleware intentionally removed — it buffers SSE (text/event-stream)
# chunks and breaks live progress streaming.


@app.on_event("startup")
async def startup():
    create_tables()
    # Initialize HPO ontology + embeddings in background (non-blocking)
    # First pipeline run may be slow if cache is cold; subsequent runs are fast
    import asyncio
    asyncio.create_task(_init_hpo_background())


async def _init_hpo_background():
    import logging
    log = logging.getLogger(__name__)
    try:
        from app.services.hpo_ontology import initialize
        await initialize()
    except Exception as e:
        log.warning(f"HPO ontology init failed (non-fatal): {e}")

    # Auto-trigger RareBench indexing once if the case index is empty.
    try:
        from app.services.case_similarity import collection_stats
        stats = collection_stats()
        if stats.get("count", 0) < 100:
            from app.tasks.indexing_tasks import index_rarebench
            index_rarebench.delay()
            log.info("Triggered RareBench case indexing (collection was empty).")
    except Exception as e:
        log.warning(f"Could not trigger case indexing: {e}")


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api")
app.include_router(cases.router, prefix="/api")
app.include_router(pipeline.router, prefix="/api")
app.include_router(report.router, prefix="/api")
app.include_router(demo.router, prefix="/api")
app.include_router(proxy.router, prefix="/api")
app.include_router(pipelines.router, prefix="/api")
app.include_router(system.router, prefix="/api")


@app.get("/api/system/status")
async def system_status():
    """Report readiness of subsystems."""
    from app.services.case_similarity import collection_stats
    status = {"mock_mode": settings.MOCK_MODE}
    try:
        status["case_index"] = collection_stats()
    except Exception:
        status["case_index"] = {"exists": False, "count": 0}
    try:
        from app.services.alphamissense import is_available
        status["alphamissense"] = is_available()
    except Exception:
        status["alphamissense"] = False
    status["franklin"] = bool(settings.FRANKLIN_API_KEY)
    return status


@app.post("/api/system/index-cases")
async def trigger_index():
    """Kick off the one-time RareBench -> Qdrant indexing (idempotent)."""
    from app.tasks.indexing_tasks import index_rarebench
    task = index_rarebench.delay()
    return {"task_id": task.id, "status": "indexing_started"}


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "mock_mode": settings.MOCK_MODE,
    }
