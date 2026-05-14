"""Approval Node — creates approval requests in PostgreSQL and UI."""
from __future__ import annotations

import json
import uuid
from typing import List

from agents.state import ApprovalRequest, OpsState, RecommendationItem
from app.core.config import settings
from app.core.logging_config import get_logger

log = get_logger(__name__)


def _persist_approval(
    recommendation: RecommendationItem,
    rec_db_id: str,
    run_id: str,
) -> ApprovalRequest:
    """Write recommendation + approval row to PostgreSQL."""
    if settings.skip_platform_db_persist:
        return ApprovalRequest(
            recommendation_id=rec_db_id,
            issue_summary=recommendation["issue_summary"],
            recommended_action=recommendation["recommendation_text"],
            impact_level=recommendation["impact_level"],
            confidence_score=recommendation["confidence_score"],
        )

    try:
        from app.core.database import get_sync_session
        from app.db.models.recommendations import Recommendation
        from app.db.models.approvals import Approval

        with get_sync_session() as session:
            rec_obj = Recommendation(
                id=uuid.UUID(rec_db_id),
                run_id=run_id,
                issue_key=recommendation["issue_key"],
                issue_summary=recommendation["issue_summary"],
                recommendation_text=recommendation["recommendation_text"],
                escalation_path=recommendation["escalation_path"],
                mitigation_steps=recommendation["mitigation_steps"],
                confidence_score=recommendation["confidence_score"],
                impact_level=recommendation["impact_level"],
                model_used=recommendation["model_used"],
            )
            session.add(rec_obj)
            session.flush()

            approval_obj = Approval(
                recommendation_id=rec_obj.id,
                run_id=run_id,
                issue_summary=recommendation["issue_summary"],
                recommended_action=recommendation["recommendation_text"],
                impact_level=recommendation["impact_level"],
                confidence_score=recommendation["confidence_score"],
                status="PENDING",
            )
            session.add(approval_obj)

        log.info("[approval] Persisted recommendation+approval for %s", rec_db_id[:8])
    except Exception as exc:
        log.warning("[approval] DB persist failed: %s", exc)

    return ApprovalRequest(
        recommendation_id=rec_db_id,
        issue_summary=recommendation["issue_summary"],
        recommended_action=recommendation["recommendation_text"],
        impact_level=recommendation["impact_level"],
        confidence_score=recommendation["confidence_score"],
    )


def approval_node(state: OpsState) -> dict:
    """Create approval request cards for AI recommendations."""
    log.info("[approval] run_id=%s", state["run_id"])

    recommendations = state.get("recommendations", [])
    run_id = state["run_id"]

    if not recommendations:
        return {
            "approval_requests": [],
            "current_node": "approval",
            "errors": [],
        }

    approvals: List[ApprovalRequest] = []
    for rec in recommendations:
        rec_id = str(uuid.uuid4())
        approval = _persist_approval(rec, rec_id, run_id)
        approvals.append(approval)
        log.info("[approval] Created approval request %s", rec_id[:8])

    log.info("[approval] Total approval requests: %d", len(approvals))
    return {
        "approval_requests": approvals,
        "current_node": "approval",
        "errors": [],
    }
