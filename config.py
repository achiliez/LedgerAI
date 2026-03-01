"""
LedgerAI — Configuration Module
Loads and validates environment variables using pydantic-settings.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    # ── Required ──────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str
    GEMINI_API_KEY: str
    DATABASE_URL: str  # async: postgresql+asyncpg://...
    DATABASE_URL_SYNC: str = ""  # sync: postgresql+psycopg2://...

    # ── Optional ──────────────────────────────────────────────
    GEMINI_MODEL: str = "gemini-2.5-flash"
    REPORT_HOUR: int = Field(default=21, ge=0, le=23)
    REPORT_MINUTE: int = Field(default=0, ge=0, le=59)
    TIMEZONE: str = "Asia/Kolkata"
    CURRENCY_SYMBOL: str = "₹"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# Singleton instance — import this everywhere
settings = Settings()  # type: ignore[call-arg]
