"""Pipeline trigger API — manually run the LangGraph orchestration."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.core.logging_config import get_logger

router = APIRouter(prefix="/pipeline", tags=["pipeline"])
log = get_logger(__name__)

# In-memory run tracker (POC — use Redis/DB in production)
_run_registry: Dict[str, Any] = {}


class TriggerResponse(BaseModel):
    run_id: str
    status: str
    message: str
    triggered_at: str


class RunStatusResponse(BaseModel):
    run_id: str
    status: str
    started_at: str
    completed_at: str | None = None
    error: str | None = None
    summary: str | None = None
    risk_count: int = 0
    approval_count: int = 0


async def _execute_pipeline(run_id: str) -> None:
    from agents.graph import run_pipeline

    _run_registry[run_id] = {
        "status": "RUNNING",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "error": None,
        "summary": None,
        "risk_count": 0,
        "approval_count": 0,
    }
    try:
        result = await run_pipeline(triggered_by="api")
        _run_registry[run_id].update({
            "status": "COMPLETED",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "summary": result.get("executive_summary", ""),
            "risk_count": len(result.get("risk_events", [])),
            "approval_count": len(result.get("approval_requests", [])),
            "state": result,
        })
        log.info("Pipeline %s completed", run_id)
    except Exception as exc:
        log.exception("Pipeline %s failed: %s", run_id, exc)
        _run_registry[run_id].update({
            "status": "FAILED",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "error": str(exc),
        })


@router.post("/trigger", response_model=TriggerResponse)
async def trigger_pipeline(background_tasks: BackgroundTasks) -> TriggerResponse:
    """Manually trigger the TG OPS AI analysis pipeline."""
    from agents.graph import run_pipeline
    import uuid

    run_id = f"manual_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:6]}"
    background_tasks.add_task(_execute_pipeline, run_id)

    return TriggerResponse(
        run_id=run_id,
        status="ACCEPTED",
        message="Pipeline queued. Poll /pipeline/status/{run_id} for updates.",
        triggered_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/status/{run_id}", response_model=RunStatusResponse)
async def get_run_status(run_id: str) -> RunStatusResponse:
    """Get status of a pipeline run."""
    if run_id not in _run_registry:
        raise HTTPException(status_code=404, detail="Run not found")
    info = _run_registry[run_id]
    return RunStatusResponse(
        run_id=run_id,
        status=info["status"],
        started_at=info["started_at"],
        completed_at=info.get("completed_at"),
        error=info.get("error"),
        summary=info.get("summary"),
        risk_count=info.get("risk_count", 0),
        approval_count=info.get("approval_count", 0),
    )


@router.get("/runs")
async def list_runs() -> list:
    """List recent pipeline runs."""
    return [
        {"run_id": k, "status": v["status"], "started_at": v["started_at"]}
        for k, v in sorted(_run_registry.items(), key=lambda x: x[1]["started_at"], reverse=True)
    ]
