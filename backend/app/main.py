from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.core.database import create_tables
from app.api.routes import pipeline, report, demo, auth, cases

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
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.on_event("startup")
async def startup():
    create_tables()


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api")
app.include_router(cases.router, prefix="/api")
app.include_router(pipeline.router, prefix="/api")
app.include_router(report.router, prefix="/api")
app.include_router(demo.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "mock_mode": settings.MOCK_MODE,
    }
