"""Notification Node — creates in-app notifications and logs them."""
from __future__ import annotations

import json
import uuid
from typing import List

from agents.state import IssueDetection, NotificationItem, OpsState
from app.core.config import settings
from app.core.logging_config import get_logger

log = get_logger(__name__)

_SEVERITY_TO_PRIORITY = {
    "INFO": "INFO",
    "WARNING": "WARNING",
    "CRITICAL": "CRITICAL",
}


def _persist_notifications(notifications: List[NotificationItem], run_id: str) -> None:
    if settings.skip_platform_db_persist:
        return
    try:
        from app.core.database import get_sync_session
        from app.db.models.notifications import Notification

        with get_sync_session() as session:
            for n in notifications:
                obj = Notification(
                    run_id=run_id,
                    priority=n["priority"],
                    channel="IN_APP",
                    title=n["title"],
                    body=n["body"],
                    entity_type=n.get("entity_type", ""),
                    entity_id=n.get("entity_id", ""),
                )
                session.add(obj)
        log.info("[notification] Persisted %d notifications", len(notifications))
    except Exception as exc:
        log.warning("[notification] DB persist failed: %s", exc)


def notification_node(state: OpsState) -> dict:
    """Build notifications for all detected issues (above and below threshold)."""
    log.info("[notification] run_id=%s", state["run_id"])

    run_id = state["run_id"]
    notifications: List[NotificationItem] = []

    # Notifications for below-threshold issues (simple alerts)
    for issue in state.get("issues_below_threshold", []):
        n = NotificationItem(
            priority=_SEVERITY_TO_PRIORITY.get(issue["severity"], "INFO"),
            title=issue["title"],
            body=issue["description"],
            entity_type=issue["issue_type"],
            entity_id=issue["issue_key"],
        )
        notifications.append(n)

    # Notifications for above-threshold issues (action required)
    for issue in state.get("issues_above_threshold", []):
        n = NotificationItem(
            priority="CRITICAL",
            title=f"[ACTION REQUIRED] {issue['title']}",
            body=f"{issue['description']} — {issue['occurrence_count']} consecutive occurrences. Recommendation pending approval.",
            entity_type=issue["issue_type"],
            entity_id=issue["issue_key"],
        )
        notifications.append(n)

    # Executive summary notification
    summary = state.get("executive_summary", "")
    if summary:
        notifications.insert(0, NotificationItem(
            priority="INFO",
            title="Executive Pipeline Summary Ready",
            body=summary[:200],
            entity_type="SUMMARY",
            entity_id=run_id,
        ))

    _persist_notifications(notifications, run_id)

    log.info("[notification] Created %d notifications", len(notifications))
    return {
        "notifications": notifications,
        "current_node": "notification",
        "errors": [],
    }
