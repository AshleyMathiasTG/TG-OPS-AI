"""Application configuration loaded from environment variables."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List

# Load .env BEFORE pydantic-settings initialises so .env values take
# precedence over any stale system/user environment variables.
_env_path = Path(__file__).parent.parent.parent.parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv(str(_env_path), override=True)

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        # .env file takes precedence over system environment variables
        # This prevents a stale system-level OPENAI_API_KEY from overriding .env
    )


    # ── App ─────────────────────────────────────────────────────────────
    app_env: str = "development"
    jwt_secret: str = "change-me"
    cors_origins: str = "http://localhost:3000"

    # ── PostgreSQL (platform DB) ─────────────────────────────────────────
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "tgops"
    postgres_password: str = "tgops"
    postgres_db: str = "tg_ops_ai"
    auto_create_schema: bool = False

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def async_postgres_dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ── MySQL (TG source DB — READ ONLY) ────────────────────────────────
    db_host: str = "10.60.20.8"
    db_user: str = "root"
    db_password: str = "devdb@r00t"
    db_name: str = "tgapdb"
    db_port: int = 3306
    mysql_query_timeout_seconds: int = 45
    mysql_max_rows: int = 5000

    @property
    def mysql_dsn(self) -> str:
        from urllib.parse import quote_plus
        # URL-encode password — critical when it contains special chars like @
        pwd = quote_plus(self.db_password)
        return (
            f"mysql+pymysql://{self.db_user}:{pwd}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    # ── Dev toggles ──────────────────────────────────────────────────────
    tgap_fixture_only: bool = True
    skip_platform_db_persist: bool = False
    disable_scheduler: bool = False

    # ── OpenAI ──────────────────────────────────────────────────────────
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Model overrides per agent role
    orchestrator_model: str = "gpt-4o"
    query_agent_model: str = "gpt-4o"
    analytics_model: str = "gpt-4o"
    format_model: str = "gpt-4o-mini"
    risk_model: str = "gpt-4o"

    # ── LangSmith ────────────────────────────────────────────────────────
    langchain_tracing_v2: bool = True
    langchain_api_key: str = ""           # set via LANGCHAIN_API_KEY in .env
    langchain_endpoint: str = "https://api.smith.langchain.com"
    langchain_project: str = "TG OPS AI"

    # ── Email ────────────────────────────────────────────────────────────
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_tls: bool = False
    email_from: str = "no-reply@tgops.ai"
    executive_to_emails: str = "exec@example.com"

    # ── Scheduler ────────────────────────────────────────────────────────
    newsletter_cron_minute: int = 0
    newsletter_cron_hour: int = 6

    # ── Business rules ───────────────────────────────────────────────────
    consecutive_issue_threshold: int = 3
    sla_aging_days: int = 5
    data_window_days: int = 60          # Rolling window for all data queries

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
