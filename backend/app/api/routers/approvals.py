"""Approvals API — manage AI recommendation approval workflow."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.db.models.approvals import Approval
from app.db.models.feedback import Feedback
from app.schemas.approvals import ApprovalDecision, FeedbackCreate
from app.core.logging_config import get_logger

router = APIRouter(prefix="/approvals", tags=["approvals"])
log = get_logger(__name__)


@router.get("")
async def list_approvals(
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=200),
    db: AsyncSession = Depends(get_db),
) -> List[Dict]:
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.data_window_days)
        stmt = (
            select(Approval)
            .where(Approval.created_at >= cutoff)
            .order_by(Approval.created_at.desc())
            .limit(limit)
        )
        if status:
            stmt = stmt.where(Approval.status == status.upper())
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "id": str(r.id),
                "recommendation_id": str(r.recommendation_id),
                "run_id": r.run_id,
                "issue_summary": r.issue_summary,
                "recommended_action": r.recommended_action,
                "escalation_path": r.escalation_path if hasattr(r, "escalation_path") else None,
                "mitigation_steps": r.mitigation_steps if hasattr(r, "mitigation_steps") else None,
                "impact_level": r.impact_level,
                "confidence_score": r.confidence_score,
                "status": r.status,
                "reviewer_note": r.reviewer_note,
                "decided_at": r.decided_at.isoformat() if r.decided_at else None,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    except Exception as exc:
        log.warning("[approvals] DB query failed: %s", exc)
        return []


@router.patch("/{approval_id}/decide")
async def decide_approval(
    approval_id: UUID,
    body: ApprovalDecision,
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """Approve or reject an AI recommendation."""
    if body.status not in ("APPROVED", "REJECTED"):
        raise HTTPException(status_code=422, detail="status must be APPROVED or REJECTED")
    try:
        await db.execute(
            update(Approval)
            .where(Approval.id == approval_id)
            .values(
                status=body.status,
                reviewer_note=body.reviewer_note,
                decided_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
    except Exception as exc:
        log.warning("[approvals] decide failed: %s", exc)

    # Simulate action execution on APPROVED
    if body.status == "APPROVED":
        log.info("[approvals] Simulating action execution for approval %s", approval_id)

    return {"approval_id": str(approval_id), "status": body.status}


@router.post("/{approval_id}/feedback")
async def submit_feedback(
    approval_id: UUID,
    body: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """Submit thumbs up/down feedback on an approval outcome."""
    if body.sentiment not in ("THUMBS_UP", "THUMBS_DOWN"):
        raise HTTPException(status_code=422, detail="sentiment must be THUMBS_UP or THUMBS_DOWN")
    try:
        fb = Feedback(
            approval_id=approval_id,
            sentiment=body.sentiment,
            comment=body.comment,
            submitted_by=body.submitted_by or "anonymous",
        )
        db.add(fb)
        await db.commit()
        return {"feedback_id": str(fb.id), "sentiment": body.sentiment}
    except Exception as exc:
        log.warning("[feedback] persist failed: %s", exc)
        return {"sentiment": body.sentiment, "status": "accepted_mock"}
