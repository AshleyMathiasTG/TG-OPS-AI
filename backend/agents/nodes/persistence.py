"""Persistence Node — saves alerts, events, and dashboard snapshot to PostgreSQL."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from agents.state import IssueDetection, OpsState
from app.core.config import settings
from app.core.logging_config import get_logger

log = get_logger(__name__)


def _persist_alerts(issues: list, run_id: str) -> None:
    if settings.skip_platform_db_persist:
        return
    try:
        from app.core.database import get_sync_session
        from app.db.models.alerts import Alert

        with get_sync_session() as session:
            for issue in issues:
                obj = Alert(
                    run_id=run_id,
                    alert_type=issue["issue_type"],
                    severity=issue["severity"],
                    title=issue["title"],
                    summary=issue["description"],
                    entity_name=issue["entity_name"],
                    entity_type=issue["issue_type"],
                    metadata_json=json.dumps(issue.get("metadata", {})),
                )
                session.add(obj)
        log.info("[persist] Saved %d alerts", len(issues))
    except Exception as exc:
        log.warning("[persist] Alert persist failed: %s", exc)


def _severity_to_risk_level(severity: str) -> str:
    """Map alert severity labels to RiskEvent risk_level enum values."""
    return {"INFO": "LOW", "WARNING": "MEDIUM", "CRITICAL": "CRITICAL"}.get(
        (severity or "").upper(), "MEDIUM"
    )


def _persist_risk_events(risk_events: list, run_id: str) -> None:
    if settings.skip_platform_db_persist:
        return
    try:
        from app.core.database import get_sync_session
        from app.db.models.risk_events import RiskEvent

        with get_sync_session() as session:
            for r in risk_events:
                obj = RiskEvent(
                    run_id=run_id,
                    risk_category=r["issue_type"],
                    risk_level=_severity_to_risk_level(r["severity"]),
                    title=r["title"],
                    description=r["description"],
                    affected_entity=r["entity_name"],
                    account_name=r["account_name"],
                    confidence_score=0.8,
                    metadata_json=json.dumps(r.get("metadata", {})),
                )
                session.add(obj)
    except Exception as exc:
        log.warning("[persist] Risk event persist failed: %s", exc)


def _persist_sla_events(sla_events: list, run_id: str) -> None:
    if settings.skip_platform_db_persist:
        return
    try:
        from app.core.database import get_sync_session
        from app.db.models.sla_events import SlaEvent

        with get_sync_session() as session:
            for s in sla_events:
                meta = s.get("metadata", {})
                obj = SlaEvent(
                    run_id=run_id,
                    sla_type=s["issue_type"],
                    breach_status="BREACHED" if s["severity"] == "CRITICAL" else "AT_RISK",
                    req_id=meta.get("req_id"),
                    account_name=s["account_name"],
                    description=s["description"],
                    aging_days=meta.get("aging_days"),
                    sla_threshold_days=settings.sla_aging_days,
                    metadata_json=json.dumps(meta),
                )
                session.add(obj)
    except Exception as exc:
        log.warning("[persist] SLA event persist failed: %s", exc)


def _persist_snapshot(state: OpsState) -> None:
    if settings.skip_platform_db_persist:
        return
    try:
        from app.core.database import get_sync_session
        from app.db.models.dashboard_snapshots import DashboardSnapshot

        analytics = state.get("analytics") or {}
        kpis = analytics.get("kpis") or {}

        # Build full blob — always include risk/recruiter/status keys even if empty
        account_risk_scores = analytics.get("account_risk_scores") or []
        recruiter_stats     = analytics.get("recruiter_stats") or []
        status_distribution = analytics.get("status_distribution") or {}

        log.info(
            "[persist] analytics keys=%s  account_risk_scores=%d  recruiter_stats=%d",
            list(analytics.keys()),
            len(account_risk_scores),
            len(recruiter_stats),
        )

        full_kpi_blob = {
            **kpis,
            "account_risk_scores": account_risk_scores,
            "recruiter_stats":     recruiter_stats,
            "status_distribution": status_distribution,
        }

        with get_sync_session() as session:
            obj = DashboardSnapshot(
                run_id=state["run_id"],
                executive_summary=state.get("executive_summary", ""),
                open_risks=len(state.get("risk_events", [])),
                sla_breaches=len(state.get("sla_events", [])),
                active_alerts=len(state.get("issues_below_threshold", [])),
                pending_approvals=len(state.get("approval_requests", [])),
                critical_issues=sum(
                    1 for i in state.get("risk_events", []) if i.get("severity") == "CRITICAL"
                ),
                kpi_json=json.dumps(full_kpi_blob),
                trend_json=json.dumps(analytics.get("trend_data") or {}),
            )
            session.add(obj)
        log.info(
            "[persist] Snapshot saved run=%s  kpi_keys=%s",
            state["run_id"], list(full_kpi_blob.keys()),
        )
    except Exception as exc:
        log.exception("[persist] Snapshot persist failed: %s", exc)


def persistence_node(state: OpsState) -> dict:
    """Persist all pipeline outputs to PostgreSQL."""
    log.info("[persist] run_id=%s", state["run_id"])

    run_id = state["run_id"]
    all_issues = list(state.get("risk_events", [])) + list(state.get("sla_events", []))

    _persist_alerts(state.get("issues_below_threshold", []), run_id)
    _persist_risk_events(state.get("risk_events", []), run_id)
    _persist_sla_events(state.get("sla_events", []), run_id)
    _persist_snapshot(state)

    log.info("[persist] Persistence complete for run %s", run_id)
    return {
        "current_node": "persistence",
        "errors": [],
    }
