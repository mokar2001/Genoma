from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "RareDx AI Diagnostic Pipeline"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://frontend:5173",
    ]

    # Mock pipeline delays (seconds) — swap with real API calls later
    DEEPRARE_MOCK_DELAY: float = 2.5
    ACMG_MOCK_DELAY: float = 2.0
    ALPHAFOLD_MOCK_DELAY: float = 3.0

    # Future real API keys (leave empty for mock mode)
    DEEPRARE_API_KEY: str = ""
    ACMG_API_KEY: str = ""
    ALPHAFOLD_API_URL: str = "https://alphafold.ebi.ac.uk/api"

    # Upload
    MAX_VCF_SIZE_MB: int = 50

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
