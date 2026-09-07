"""
Application configuration using Pydantic Settings.
Loads and validates environment variables from .env or container environment.
"""
from typing import List, Optional
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "ORCA Marine Intelligence"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    LOG_LEVEL: str = "info"

    SECRET_KEY: str = "default-insecure-secret-key-change-in-production"
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # ── LLM / AI Provider ──────────────────────────────────────────────
    LLM_API_KEY: str = ""
    LLM_PROVIDER: str = "google"  # e.g. "google", "openai", "anthropic"
    LLM_MODEL: str = "gemini-flash-lite-latest"  # e.g. "gemini-flash-lite-latest", "gemini-3.5-flash", "gpt-4o-mini"
    LLM_BASE_URL: Optional[str] = None  # custom endpoint for local/proxy LLM servers
    LLM_TEMPERATURE: float = 0.2
    LLM_TIMEOUT_SECONDS: float = 20.0

    # ── ISRO Bhuvan Geoportal ──────────────────────────────────────────
    BHUVAN_ACCESS_TOKEN: str = ""

    # ── India Meteorological Department (optional) ─────────────────────
    IMD_API_KEY: Optional[str] = None

    # ── Database & Vector Store ────────────────────────────────────────
    DATABASE_URL: str = ""
    VECTOR_DB_PATH: str = ""

    # ── External ISRO / INCOIS / NavIC API Credentials ─────────────────
    MOSDAC_API_BASE_URL: str = "https://mosdac.gov.in/api"
    MOSDAC_API_KEY: str = ""
    MOSDAC_USERNAME: str = ""
    MOSDAC_PASSWORD: str = ""
    MOSDAC_DATASET_ID: str = "E06OCM_L4_AC"
    MOSDAC_NETCDF_PATH: str = r"C:\home\sys_oper\MOSDAC_Downloads\E06OCML4AC_20260903_25km_v1.0.1.nc"
    MOSDAC_DOWNLOAD_DIR: str = r"C:\home\sys_oper\MOSDAC_Downloads"
    MOSDAC_REMOTE_URL: Optional[str] = None
    MOSDAC_MAX_FILE_AGE_HOURS: float = 24.0
    MOSDAC_DOWNLOAD_TIMEOUT: float = 30.0
    MOSDAC_AUTO_DOWNLOAD_ENABLED: bool = False
    MOSDAC_MAX_CACHED_FILES: int = 2
    MOSDAC_LOOKBACK_DAYS: int = 3
    MOSDAC_DOWNLOAD_COUNT: int = 1
    MOSDAC_REFRESH_INTERVAL_HOURS: float = 24.0
    MOSDAC_BOUNDING_BOX: str = "60,5,95,25"
    MOSDAC_CLIENT_PATH: Optional[str] = None

    INCOIS_ERDDAP_BASE_URL: str = "https://erddap.incois.gov.in/erddap"
    INCOIS_API_KEY: str = ""

    NAVIC_GATEWAY_URL: str = "https://navic-hub.isro.gov.in/api"
    NAVIC_API_KEY: str = ""

    # ── Emergency & Alerting Gateways ──────────────────────────────────
    COAST_GUARD_MRCC_WEBHOOK_URL: str = "https://mrcc-alerts.indiancoastguard.gov.in/webhook"
    SMS_GATEWAY_API_URL: str = "https://sms-gateway.gov.in/api/send"
    SMS_GATEWAY_API_KEY: str = ""

    # ── Background polling frequency ───────────────────────────────────
    ALERT_POLL_INTERVAL_SECONDS: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
