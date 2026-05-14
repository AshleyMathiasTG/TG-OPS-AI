"""Dashboard response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class KpiCard(BaseModel):
    label: str
    value: int
    delta: Optional[int] = None
    trend: str = "stable"  # up | down | stable
    severity: str = "normal"  # normal | warning | critical


class ExecutiveSummaryResponse(BaseModel):
    run_id: str
    summary: str
    highlights: List[str]
    generated_at: datetime
    kpis: List[KpiCard]


class AccountRiskScore(BaseModel):
    account: str
    score: int
    submissions: int
    no_shows: int
    rejections: int
    aging_critical: int


class RecruiterStat(BaseModel):
    recruiter: str
    active: int
    no_shows: int
    rejections: int


class TrendData(BaseModel):
    weeks: List[str]
    sla_breaches: List[int]
    no_shows: List[int]
    tech_rejections: List[int]
    open_positions: List[int]


class DashboardResponse(BaseModel):
    run_id: str
    executive_summary: str
    executive_highlights: List[str]
    kpis: Dict[str, Any]
    account_risk_scores: List[AccountRiskScore]
    recruiter_stats: List[RecruiterStat]
    trend_data: TrendData
    generated_at: datetime
    active_alerts: int
    pending_approvals: int
