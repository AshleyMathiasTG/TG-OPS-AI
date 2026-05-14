"""Dashboard API — executive summary, KPIs, trends."""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.core.logging_config import get_logger
from app.db.models.dashboard_snapshots import DashboardSnapshot
from app.db.models.alerts import Alert
from app.db.models.approvals import Approval

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
log = get_logger(__name__)


def _empty_dashboard() -> Dict[str, Any]:
    """Return a zero-state dashboard response — no data yet, pipeline not run."""
    return {
        "run_id": None,
        "executive_summary": None,
        "executive_highlights": [],
        "kpis": {
            "open_positions": 0, "total_submissions": 0,
            "aging_critical": 0, "aging_at_risk": 0,
            "no_shows": 0, "budget_mismatch": 0,
            "tech_rejections": 0, "on_hold": 0,
        },
        "account_risk_scores": [],
        "recruiter_stats": [],
        "trend_data": {"weeks": [], "sla_breaches": [], "no_shows": [], "tech_rejections": [], "open_positions": []},
        "active_alerts": 0,
        "pending_approvals": 0,
        "generated_at": None,
    }


@router.get("/summary")
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Get latest dashboard snapshot with all KPIs and trends."""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.data_window_days)

        stmt = (
            select(DashboardSnapshot)
            .where(DashboardSnapshot.created_at >= cutoff)
            .order_by(DashboardSnapshot.created_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        snapshot = result.scalar_one_or_none()

        if snapshot:
            full_kpis = json.loads(snapshot.kpi_json or "{}")
            trend_data = json.loads(snapshot.trend_json or "{}")

            # Extract risk/recruiter data from blob (saved by persistence.py)
            account_risk_scores = full_kpis.pop("account_risk_scores", [])
            recruiter_stats     = full_kpis.pop("recruiter_stats", [])
            full_kpis.pop("status_distribution", None)

            # Count alerts/approvals from THIS specific run only (avoids accumulation)
            alerts_count = await db.scalar(
                select(func.count(Alert.id))
                .where(
                    Alert.is_dismissed == False,
                    Alert.run_id == snapshot.run_id,
                )
            )
            approvals_count = await db.scalar(
                select(func.count(Approval.id))
                .where(
                    Approval.status == "PENDING",
                    Approval.run_id == snapshot.run_id,
                )
            )

            # Build executive highlights from summary text
            summary_text = snapshot.executive_summary or ""
            highlights = [s.strip() for s in summary_text.split(".") if len(s.strip()) > 20][:6]

            return {
                "run_id": snapshot.run_id,
                "executive_summary": summary_text,
                "executive_highlights": highlights,
                "kpis": full_kpis,
                "trend_data": trend_data,
                "account_risk_scores": account_risk_scores,
                "recruiter_stats": recruiter_stats,
                "active_alerts": alerts_count or 0,
                "pending_approvals": approvals_count or 0,
                "generated_at": snapshot.created_at.isoformat(),
            }
    except Exception as exc:
        log.warning("[dashboard] DB query failed: %s", exc)

    return _empty_dashboard()


@router.get("/snapshots")
async def list_snapshots(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
) -> List[Dict]:
    """List recent pipeline run snapshots within the rolling window."""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.data_window_days)
        stmt = (
            select(DashboardSnapshot)
            .where(DashboardSnapshot.created_at >= cutoff)
            .order_by(DashboardSnapshot.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "run_id": r.run_id,
                "open_risks": r.open_risks,
                "sla_breaches": r.sla_breaches,
                "active_alerts": r.active_alerts,
                "pending_approvals": r.pending_approvals,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    except Exception as exc:
        log.warning("[dashboard] snapshots query failed: %s", exc)
        return []
