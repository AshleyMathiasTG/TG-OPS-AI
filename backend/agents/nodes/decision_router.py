"""Decision Router — checks consecutive issue counts and routes accordingly."""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

from agents.state import IssueDetection, OpsState
from app.core.config import settings
from app.core.logging_config import get_logger

log = get_logger(__name__)

THRESHOLD = settings.consecutive_issue_threshold


def _load_occurrence_counts(issue_keys: List[str]) -> Dict[str, int]:
    """Look up current occurrence counts from PostgreSQL."""
    if settings.skip_platform_db_persist:
        # Return simulated counts for dev
        simulated = {
            key: 3 if idx < 2 else 1
            for idx, key in enumerate(issue_keys)
        }
        return simulated

    try:
        from app.core.database import get_sync_session
        from app.db.models.issue_occurrences import IssueOccurrence
        from sqlalchemy import select

        with get_sync_session() as session:
            stmt = select(IssueOccurrence).where(IssueOccurrence.issue_key.in_(issue_keys))
            rows = session.execute(stmt).scalars().all()
            return {r.issue_key: r.occurrence_count for r in rows}
    except Exception as exc:
        log.warning("[router] Cannot load occurrence counts: %s", exc)
        return {}


def _upsert_occurrence(issue: IssueDetection, run_id: str) -> int:
    """Increment occurrence count in DB and return new count.

    Resets count to 1 if the issue was last seen more than `data_window_days` ago —
    this prevents stale accumulation from old pipeline runs.
    """
    if settings.skip_platform_db_persist:
        return issue.get("occurrence_count", 1)

    try:
        from app.core.database import get_sync_session
        from app.db.models.issue_occurrences import IssueOccurrence
        from sqlalchemy import select

        window_cutoff = datetime.now(timezone.utc) - timedelta(days=settings.data_window_days)

        with get_sync_session() as session:
            stmt = select(IssueOccurrence).where(
                IssueOccurrence.issue_key == issue["issue_key"]
            )
            row = session.execute(stmt).scalar_one_or_none()
            if row:
                # Reset count if issue hasn't been seen within the rolling window
                last_seen = row.last_seen_at
                if last_seen and last_seen.tzinfo is None:
                    from datetime import timezone as _tz
                    last_seen = last_seen.replace(tzinfo=_tz.utc)
                if last_seen and last_seen < window_cutoff:
                    row.occurrence_count = 1  # stale — reset
                    log.info("[router] Reset stale count for %s (last_seen=%s)", issue["issue_key"][:16], last_seen)
                else:
                    row.occurrence_count += 1
                row.last_detected_run = run_id
                row.last_seen_at = datetime.now(timezone.utc)
                count = row.occurrence_count
            else:
                row = IssueOccurrence(
                    issue_key=issue["issue_key"],
                    issue_type=issue["issue_type"],
                    entity_name=issue["entity_name"],
                    account_name=issue["account_name"],
                    occurrence_count=1,
                    last_detected_run=run_id,
                    metadata_json=json.dumps(issue.get("metadata", {})),
                )
                session.add(row)
                count = 1
            return count
    except Exception as exc:
        log.warning("[router] Cannot upsert occurrence: %s", exc)
        return 1


def decision_router_node(state: OpsState) -> dict:
    """Route issues based on consecutive occurrence count vs threshold."""
    log.info("[router] run_id=%s threshold=%d", state["run_id"], THRESHOLD)

    all_issues: List[IssueDetection] = list(state.get("risk_events", [])) + list(state.get("sla_events", []))
    run_id = state["run_id"]

    above: List[IssueDetection] = []
    below: List[IssueDetection] = []

    for issue in all_issues:
        count = _upsert_occurrence(issue, run_id)
        updated = {**issue, "occurrence_count": count}
        if count >= THRESHOLD:
            above.append(updated)
            log.info("[router] ABOVE threshold: %s (count=%d)", issue["issue_key"][:16], count)
        else:
            below.append(updated)

    log.info("[router] above=%d below=%d", len(above), len(below))

    return {
        "issues_above_threshold": above,
        "issues_below_threshold": below,
        "current_node": "decision_router",
        "errors": [],
    }
