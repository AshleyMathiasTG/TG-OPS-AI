"""Analytics API — KPI trends, account risk, recruiter stats."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.db.models.dashboard_snapshots import DashboardSnapshot
from app.db.models.alerts import Alert
from app.db.models.risk_events import RiskEvent
from app.core.logging_config import get_logger

router = APIRouter(prefix="/analytics", tags=["analytics"])
log = get_logger(__name__)


def _risk_label(score: int) -> str:
    if score >= 10:
        return "CRITICAL"
    if score >= 6:
        return "HIGH"
    if score >= 3:
        return "MEDIUM"
    return "LOW"


def _empty_analytics() -> Dict[str, Any]:
    return {
        "status_distribution": {},
        "risk_by_account": [],
        "recruiter_performance": [],
        "trend": {"weeks": [], "sla_breaches": [], "no_shows": [], "tech_rejections": [], "open_positions": [], "budget_mismatch": []},
        "top_issues": [],
    }


@router.get("/kpis")
async def get_kpi_trends(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Get trend data from historical snapshots within the rolling window."""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.data_window_days)
        stmt = (
            select(DashboardSnapshot)
            .where(DashboardSnapshot.created_at >= cutoff)
            .order_by(DashboardSnapshot.created_at.desc())
            .limit(10)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        if rows:
            return {
                "snapshots": [
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
            }
    except Exception as exc:
        log.warning("[analytics] trend query failed: %s", exc)
    return {}


@router.get("/risk-heatmap")
async def get_risk_heatmap(db: AsyncSession = Depends(get_db)) -> List[Dict]:
    """Get account-level risk scores from the latest snapshot within the rolling window."""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.data_window_days)
        stmt = (
            select(DashboardSnapshot)
            .where(DashboardSnapshot.created_at >= cutoff)
            .order_by(DashboardSnapshot.created_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        snap = result.scalar_one_or_none()
        if snap and snap.kpi_json:
            kpis = json.loads(snap.kpi_json)
            return kpis.get("account_risk_scores", [])
    except Exception as exc:
        log.warning("[analytics] heatmap query failed: %s", exc)
    return []


@router.get("/overview")
async def get_full_analytics(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Build full analytics from snapshots + live DB counts within the rolling window."""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.data_window_days)

        # Fetch latest snapshot within the window
        snap_stmt = (
            select(DashboardSnapshot)
            .where(DashboardSnapshot.created_at >= cutoff)
            .order_by(DashboardSnapshot.created_at.desc())
            .limit(1)
        )
        snap_result = await db.execute(snap_stmt)
        snap = snap_result.scalar_one_or_none()

        # Fetch up to 10 snapshots within the window for trend
        trend_stmt = (
            select(DashboardSnapshot)
            .where(DashboardSnapshot.created_at >= cutoff)
            .order_by(DashboardSnapshot.created_at.desc())
            .limit(10)
        )
        trend_result = await db.execute(trend_stmt)
        trend_rows = list(reversed(trend_result.scalars().all()))

        # Fetch alert type distribution within the window
        alert_stmt = select(Alert.alert_type, func.count(Alert.id)).where(
            Alert.is_dismissed == False,
            Alert.created_at >= cutoff,
        ).group_by(Alert.alert_type)
        alert_result = await db.execute(alert_stmt)
        alert_dist = dict(alert_result.all())

        if snap and snap.kpi_json:
            kpi_blob = json.loads(snap.kpi_json)
            account_risk_scores = kpi_blob.get("account_risk_scores", [])
            recruiter_stats = kpi_blob.get("recruiter_stats", [])
            status_dist = kpi_blob.get("status_distribution", {})

            # Build account risk for analytics format
            risk_by_account = [
                {"account": r["account"], "score": r["score"], "label": _risk_label(r["score"])}
                for r in account_risk_scores
            ] if account_risk_scores else []

            # Build recruiter performance with load_score
            max_active = max((r.get("active", 1) for r in recruiter_stats), default=1)
            recruiter_performance = [
                {**r, "load_score": round((r.get("active", 0) / max(max_active, 1)) * 100)}
                for r in recruiter_stats
            ] if recruiter_stats else []

            # Build trend from historical snapshots
            if trend_rows:
                weeks = [f"W-{len(trend_rows)-1-i}" if i < len(trend_rows)-1 else "Current"
                         for i in range(len(trend_rows))]
                trend = {
                    "weeks": weeks,
                    "sla_breaches": [r.sla_breaches for r in trend_rows],
                    "no_shows": [json.loads(r.kpi_json or "{}").get("no_shows", 0) for r in trend_rows],
                    "tech_rejections": [json.loads(r.kpi_json or "{}").get("tech_rejections", 0) for r in trend_rows],
                    "open_positions": [json.loads(r.kpi_json or "{}").get("open_positions", 0) for r in trend_rows],
                    "budget_mismatch": [json.loads(r.kpi_json or "{}").get("budget_mismatch", 0) for r in trend_rows],
                }
            else:
                trend = _empty_analytics()["trend"]

            # Top issues from alert distribution or status distribution
            combined_dist = {**status_dist, **{k: v for k, v in alert_dist.items() if k not in status_dist}}
            top_issues = [
                {"type": k.replace("_", " ").title(), "count": v, "trend": "up"}
                for k, v in sorted(combined_dist.items(), key=lambda x: x[1], reverse=True)
                if v > 0
            ][:6]

            # Readable status distribution labels
            readable_dist = {k.replace("_", " ").title(): v for k, v in status_dist.items() if v > 0}
            if not readable_dist:
                readable_dist = {k.replace("_", " ").title(): v for k, v in alert_dist.items() if v > 0}

            return {
                "status_distribution": readable_dist,
                "risk_by_account": risk_by_account,
                "recruiter_performance": recruiter_performance,
                "trend": trend,
                "top_issues": top_issues,
            }

    except Exception as exc:
        log.warning("[analytics] overview query failed: %s", exc)

    return _empty_analytics()
