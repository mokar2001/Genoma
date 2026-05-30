from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "RareDx AI Diagnostic Pipeline"
    APP_VERSION: str = "0.2.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./raredx.db"

    # Auth
    SECRET_KEY: str = "change-this-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 1 week

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://frontend:5173",
    ]

    # LLM (any one is enough)
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"  # or claude-3-haiku-20240307

    # Pipeline delays for mock mode (when no LLM key)
    MOCK_MODE: bool = True  # auto-disabled when API key present

    # Upload
    MAX_VCF_SIZE_MB: int = 50

    # Local VCF fallback
    LOCAL_VCF_PATH: str = ""

    # Legacy mock delay settings (kept for compatibility)
    DEEPRARE_MOCK_DELAY: float = 2.5
    ACMG_MOCK_DELAY: float = 2.0
    ALPHAFOLD_MOCK_DELAY: float = 3.0
    ALPHAFOLD_API_URL: str = "https://alphafold.ebi.ac.uk/api"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
# Auto-disable mock if LLM key provided
if settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY:
    settings.MOCK_MODE = False
