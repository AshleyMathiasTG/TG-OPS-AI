"""
APScheduler-based pipeline trigger for TG OPS AI.

Schedule: once daily at 06:00 UTC (configurable).
After each run a clean in-app "Daily Summary" notification is persisted to PostgreSQL.
No email is sent.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.logging_config import get_logger

log = get_logger(__name__)

_scheduler = BackgroundScheduler(timezone="UTC")


# ── Daily summary notification ────────────────────────────────────────────────

def _build_summary_body(result: dict) -> str:
    """
    Compose a clean, readable daily summary body for the in-app notification.
    Format:
        TG OPS AI — Daily Operational Summary
        ─────────────────────────────────────
        <executive summary>

        Key Metrics
          • Open Positions  : N
          • SLA Breaches    : N
          • Active Alerts   : N
          • Pending Approvals: N

        Issues Detected: N critical, N total
        Approvals Awaiting: N
    """
    analytics = result.get("analytics", {})
    kpis = analytics.get("kpis", {})
    risks = result.get("risk_events", [])
    approvals = result.get("approval_requests", [])
    summary = result.get("executive_summary", "No summary generated.")

    critical_count = sum(1 for r in risks if r.get("severity") == "CRITICAL")
    run_time = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")

    lines = [
        f"TG OPS AI — Daily Operational Summary",
        f"Run: {run_time}",
        "",
        summary,
        "",
        "─── Key Metrics ───────────────────────────",
        f"  Open Positions   : {kpis.get('open_positions', 0)}",
        f"  SLA Breaches     : {kpis.get('aging_critical', 0)}",
        f"  At-Risk Submissions: {kpis.get('aging_at_risk', 0)}",
        f"  Interview No-Shows : {kpis.get('no_shows', 0)}",
        f"  Budget Mismatches  : {kpis.get('budget_mismatch', 0)}",
        f"  Tech Rejections    : {kpis.get('tech_rejections', 0)}",
        "",
        f"─── Detections ────────────────────────────",
        f"  Total Issues     : {len(risks)}",
        f"  Critical         : {critical_count}",
        f"  Pending Approvals: {len(approvals)}",
    ]

    # Add top critical issue titles
    critical_issues = [r for r in risks if r.get("severity") == "CRITICAL"][:3]
    if critical_issues:
        lines.append("")
        lines.append("─── Critical Items ─────────────────────────")
        for issue in critical_issues:
            lines.append(f"  • {issue.get('title', '')}")

    return "\n".join(lines)


def _persist_daily_summary(result: dict, run_id: str) -> None:
    """Write the daily summary as an in-app notification to PostgreSQL."""
    try:
        from app.core.database import get_sync_session
        from app.db.models.notifications import Notification

        risks = result.get("risk_events", [])
        approvals = result.get("approval_requests", [])
        critical_count = sum(1 for r in risks if r.get("severity") == "CRITICAL")

        priority = "CRITICAL" if critical_count > 0 else ("WARNING" if len(risks) > 0 else "INFO")
        title = (
            f"[{datetime.now(timezone.utc).strftime('%d %b')}] Daily Summary — "
            f"{critical_count} critical, {len(risks)} issues, {len(approvals)} approval(s) pending"
        )
        body = _build_summary_body(result)

        with get_sync_session() as session:
            obj = Notification(
                run_id=run_id,
                priority=priority,
                channel="IN_APP",
                title=title,
                body=body,
                entity_type="DAILY_SUMMARY",
                entity_id=run_id,
            )
            session.add(obj)
        log.info("[scheduler] Daily summary notification persisted (run=%s)", run_id)
    except Exception as exc:
        log.warning("[scheduler] Failed to persist daily summary: %s", exc)


# ── Pipeline runner ────────────────────────────────────────────────────────────

def _run_pipeline_sync() -> None:
    """Synchronous wrapper to run async pipeline from APScheduler thread."""
    started_at = datetime.now(timezone.utc)
    log.info("[scheduler] Daily pipeline triggered at %s", started_at.isoformat())
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        from agents.graph import run_pipeline
        result = loop.run_until_complete(run_pipeline(triggered_by="scheduler_daily"))

        risks = len(result.get("risk_events", []))
        approvals = len(result.get("approval_requests", []))
        sla = len(result.get("sla_events", []))
        run_id = result.get("run_id", f"scheduler_{started_at.strftime('%Y%m%d_%H%M%S')}")

        log.info(
            "[scheduler] Pipeline complete — risks=%d sla=%d approvals=%d",
            risks, sla, approvals,
        )

        # Post clean daily summary notification (no email)
        _persist_daily_summary(result, run_id)

    except Exception as exc:
        log.exception("[scheduler] Pipeline run failed: %s", exc)
    finally:
        loop.close()


# ── Scheduler lifecycle ───────────────────────────────────────────────────────

def start_scheduler() -> None:
    """Start the background scheduler with daily 06:00 UTC cron trigger."""
    if _scheduler.running:
        log.warning("[scheduler] Already running, skipping start")
        return

    _scheduler.add_job(
        _run_pipeline_sync,
        trigger=CronTrigger(
            hour=settings.newsletter_cron_hour,
            minute=settings.newsletter_cron_minute,
            timezone="UTC",
        ),
        id="daily_pipeline",
        name="TG OPS AI Daily Pipeline (06:00 UTC)",
        replace_existing=True,
        misfire_grace_time=600,  # 10-min grace if server was briefly down
    )

    _scheduler.start()
    log.info(
        "[scheduler] Started — daily at %02d:%02d UTC",
        settings.newsletter_cron_hour,
        settings.newsletter_cron_minute,
    )


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("[scheduler] Stopped")
