"""Approval and recommendation schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ApprovalResponse(BaseModel):
    id: UUID
    recommendation_id: UUID
    run_id: str
    issue_summary: str
    recommended_action: str
    impact_level: Optional[str] = None
    confidence_score: Optional[float] = None
    status: str
    reviewer_note: Optional[str] = None
    decided_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApprovalDecision(BaseModel):
    status: str  # APPROVED | REJECTED
    reviewer_note: Optional[str] = None


class FeedbackCreate(BaseModel):
    sentiment: str  # THUMBS_UP | THUMBS_DOWN
    comment: Optional[str] = None
    submitted_by: Optional[str] = "anonymous"


class FeedbackResponse(BaseModel):
    id: UUID
    approval_id: UUID
    sentiment: str
    comment: Optional[str] = None
    submitted_by: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
