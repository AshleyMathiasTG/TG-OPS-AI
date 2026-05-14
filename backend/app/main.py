"""TG OPS AI — FastAPI application entry point."""
from __future__ import annotations

# ── Set LangSmith / LangChain tracing env vars FIRST ─────────────────────────
# These MUST be in os.environ before any langchain* package is imported.
import os as _os
import sys
from pathlib import Path

_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    try:
        from dotenv import load_dotenv as _ld
        _ld(str(_env_path), override=True)
    except ImportError:
        pass

# Force-set LangSmith vars from .env (dotenv already loaded above)
_os.environ.setdefault("LANGCHAIN_TRACING_V2", _os.getenv("LANGCHAIN_TRACING_V2", "false"))
_ls_key = _os.getenv("LANGCHAIN_API_KEY", "")
if _ls_key:
    _os.environ["LANGCHAIN_API_KEY"]    = _ls_key
    _os.environ["LANGCHAIN_TRACING_V2"] = "true"
    _os.environ["LANGCHAIN_ENDPOINT"]   = _os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
    _os.environ["LANGCHAIN_PROJECT"]    = _os.getenv("LANGCHAIN_PROJECT", "TG OPS AI")
# ─────────────────────────────────────────────────────────────────────────────

from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure the project root is on PYTHONPATH so `agents.*` can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import check_postgres_health
from app.core.logging_config import configure_logging, get_logger
from app.api.routers import pipeline, dashboard, alerts, approvals, notifications, analytics

configure_logging("DEBUG" if settings.app_env == "development" else "INFO")
log = get_logger("tg_ops_ai.main")

# Ensure settings values override any pre-existing stale env vars
if settings.langchain_api_key:
    _os.environ["LANGCHAIN_API_KEY"]    = settings.langchain_api_key
    _os.environ["LANGCHAIN_TRACING_V2"] = "true" if settings.langchain_tracing_v2 else "false"
    _os.environ["LANGCHAIN_ENDPOINT"]   = settings.langchain_endpoint
    _os.environ["LANGCHAIN_PROJECT"]    = settings.langchain_project
    log.info("LangSmith tracing enabled — project=%s  key=...%s",
             settings.langchain_project, settings.langchain_api_key[-8:])
else:
    _os.environ["LANGCHAIN_TRACING_V2"] = "false"
    log.info("LangSmith tracing disabled (no API key configured)")


# ── Lifespan (startup / shutdown) ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("=== TG OPS AI Backend starting (env=%s  fixture=%s) ===",
             settings.app_env, settings.tgap_fixture_only)

    # Auto-create schema if configured
    if settings.auto_create_schema:
        try:
            from app.db.base import Base
            from app.db.models import (  # noqa: F401 — ensure all models registered
                Alert, RiskEvent, SlaEvent, Recommendation,
                Approval, Feedback, Notification, ExecutionLog,
                IssueOccurrence, DashboardSnapshot,
            )
            from app.core.database import sync_engine
            Base.metadata.create_all(bind=sync_engine)
            log.info("Database schema ensured (auto_create_schema=true)")
        except Exception as exc:
            log.warning("Schema auto-create failed (non-fatal): %s", exc)

    # Start scheduler
    if not settings.disable_scheduler:
        try:
            from scheduler.pipeline_scheduler import start_scheduler
            start_scheduler()
            log.info("Scheduler started")
        except Exception as exc:
            log.warning("Scheduler start failed (non-fatal): %s", exc)

    yield

    log.info("=== TG OPS AI Backend shutting down ===")
    if not settings.disable_scheduler:
        try:
            from scheduler.pipeline_scheduler import stop_scheduler
            stop_scheduler()
        except Exception:
            pass


# ── Application factory ───────────────────────────────────────────────────────

app = FastAPI(
    title="TG OPS AI",
    description="AI-powered operational intelligence platform for recruitment & delivery operations.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(pipeline.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(approvals.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["meta"])
async def health() -> Dict[str, Any]:
    pg_ok = await check_postgres_health()
    return {
        "status": "ok",
        "service": "tg-ops-ai",
        "version": "1.0.0",
        "env": settings.app_env,
        "postgres": "ok" if pg_ok else "degraded",
        "fixture_mode": settings.tgap_fixture_only,
        "langsmith_enabled": bool(settings.langchain_api_key),
        "data_window_days": settings.data_window_days,
    }


@app.get("/", tags=["meta"])
async def root() -> Dict[str, str]:
    return {"message": "TG OPS AI — Operational Intelligence Platform", "docs": "/api/docs"}
