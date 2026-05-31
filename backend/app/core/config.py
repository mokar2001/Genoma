from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    APP_NAME: str = "RareDx AI Diagnostic Platform"
    APP_VERSION: str = "0.3.0"
    DEBUG: bool = True

    # ── Infrastructure ────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://raredx:raredx_secret@postgres:5432/raredx"
    REDIS_URL: str = "redis://redis:6379/0"
    QDRANT_URL: str = "http://qdrant:6333"
    DATA_DIR: str = "/data"
    # Host path of the data dir — needed so Nextflow's child containers
    # (spawned via mounted docker.sock) mount the correct host paths.
    HOST_DATA_DIR: str = os.getenv("HOST_DATA_DIR", "/data")
    NXF_HOME: str = os.getenv("NXF_HOME", "/data/.nextflow")

    # ── Auth ──────────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-this-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://frontend:5173",
    ]

    # ── LLM ───────────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""
    ANTHROPIC_API_KEY: str = ""
    LLM_MODEL: str = "qwen2.5:1.5b"
    MOCK_MODE: bool = True

    # ── External variant tools ────────────────────────────────────────────────
    FRANKLIN_API_KEY: str = ""        # Genoox Franklin — gated until provided
    FRANKLIN_API_URL: str = "https://api.genoox.com"
    ALPHAMISSENSE_TSV: str = "/data/resources/AlphaMissense_hg38.tsv.gz"

    # ── Compute budget (server: 32GB RAM / 8 cores) ───────────────────────────
    NF_MAX_MEMORY: str = "28.GB"
    NF_MAX_CPUS: int = 7
    NF_MAX_TIME: str = "48.h"

    # ── Reference genome for nf-core ──────────────────────────────────────────
    GENOME_BUILD: str = "GATK.GRCh38"

    # ── Upload limits ─────────────────────────────────────────────────────────
    MAX_UPLOAD_GB: int = 200

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

# Auto-disable mock mode when an LLM endpoint is configured
if settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY:
    settings.MOCK_MODE = False
