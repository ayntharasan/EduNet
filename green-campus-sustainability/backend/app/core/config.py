"""Application configuration loaded from environment variables / .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "Green Campus Sustainability Auditor"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "sqlite:///./green_campus.db"

    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    MAX_UPLOAD_SIZE_MB: int = 50
    UPLOAD_DIR: str = "uploads"

    DEFAULT_EMISSION_FACTOR: float = 0.716  # kgCO2e/kWh - CEA India 2022-23
    EMISSION_FACTOR_SOURCE: str = "CEA CO2 Baseline Database Version 18 (2022-23)"
    EMISSION_FACTOR_UNIT: str = "kgCO2e/kWh"

    OLLAMA_BASE_URL: str = ""
    OLLAMA_MODEL: str = ""
    OLLAMA_ENABLED: bool = False

    DEMO_SEED: int = 42
    DEMO_CAMPUS_NAME: str = "Green Valley University (Demo)"


settings = Settings()
