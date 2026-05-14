"""LangGraph shared state definition for the TG OPS AI orchestration graph."""
from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypedDict
import operator


class IssueDetection(TypedDict):
    issue_key: str          # unique deterministic key for this issue type+entity
    issue_type: str         # e.g. "INTERVIEW_NO_SHOW"
    title: str
    severity: str           # INFO | WARNING | CRITICAL
    entity_name: str
    account_name: str
    occurrence_count: int
    description: str
    metadata: Dict[str, Any]


class RecommendationItem(TypedDict):
    issue_key: str
    issue_summary: str
    recommendation_text: str
    escalation_path: str
    mitigation_steps: str
    confidence_score: float
    impact_level: str
    model_used: str


class ApprovalRequest(TypedDict):
    recommendation_id: str  # UUID string set after DB write
    issue_summary: str
    recommended_action: str
    impact_level: str
    confidence_score: float


class NotificationItem(TypedDict):
    priority: str
    title: str
    body: str
    entity_type: str
    entity_id: str


class OpsState(TypedDict):
    # ── Run metadata ──────────────────────────────────────────────────────
    run_id: str
    triggered_at: str

    # ── Raw data from TG DB ───────────────────────────────────────────────
    raw_data: Dict[str, Any]

    # ── Cleaned / normalised data ─────────────────────────────────────────
    cleaned_data: Dict[str, Any]

    # ── Agent outputs ─────────────────────────────────────────────────────
    executive_summary: str
    executive_highlights: List[str]

    # Detected issues (accumulate across nodes)
    risk_events: Annotated[List[IssueDetection], operator.add]
    sla_events: Annotated[List[IssueDetection], operator.add]

    # Analytics KPIs
    analytics: Dict[str, Any]

    # Consecutive detection results
    issues_above_threshold: List[IssueDetection]   # count >= 3
    issues_below_threshold: List[IssueDetection]   # count < 3

    # Agent outputs
    recommendations: List[RecommendationItem]
    approval_requests: List[ApprovalRequest]
    notifications: Annotated[List[NotificationItem], operator.add]

    # ── Execution tracking ────────────────────────────────────────────────
    errors: Annotated[List[str], operator.add]
    current_node: str
