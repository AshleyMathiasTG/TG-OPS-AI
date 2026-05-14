"""Analytics Agent — computes KPIs, trends, and metrics from operational data."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any, Dict, List

from agents.state import OpsState
from app.core.logging_config import get_logger

log = get_logger(__name__)


def analytics_node(state: OpsState) -> dict:
    """Compute KPIs, account metrics, recruiter stats, and trend data."""
    log.info("[analytics] run_id=%s", state["run_id"])

    cleaned = state.get("cleaned_data", {})
    submissions = cleaned.get("submissions", [])
    positions = cleaned.get("open_positions", [])
    rejections = cleaned.get("rejections", [])
    interviews = cleaned.get("interviews", [])

    # ── KPI metrics ───────────────────────────────────────────────────────
    total_positions = len(positions)
    total_submissions = len(submissions)
    aging_critical = sum(1 for p in positions if p.get("aging_tag") == "CRITICAL")
    aging_at_risk = sum(1 for p in positions if p.get("aging_tag") == "AT_RISK")

    status_counts = Counter(s.get("canonical_status", "UNKNOWN") for s in submissions)
    no_shows = status_counts.get("INTERVIEW_NO_SHOW", 0)
    budget_mismatch = status_counts.get("BUDGET_MISMATCH", 0)
    tech_rejections = status_counts.get("TECH_REJECTION", 0)
    on_hold = status_counts.get("HOLD", 0)

    no_show_interviews = sum(1 for i in interviews if str(i.get("interview_status", "")).lower() == "no-show")

    # ── Account-level breakdown ───────────────────────────────────────────
    account_map: Dict[str, Dict] = defaultdict(lambda: {
        "submissions": 0, "no_shows": 0, "rejections": 0, "aging_critical": 0
    })
    for s in submissions:
        acc = s.get("account_name", "Unknown")
        account_map[acc]["submissions"] += 1
        status = s.get("canonical_status", "")
        if status == "INTERVIEW_NO_SHOW":
            account_map[acc]["no_shows"] += 1
        elif "REJECTION" in status or "REJECTED" in status:
            account_map[acc]["rejections"] += 1
        if s.get("aging_tag") == "CRITICAL":
            account_map[acc]["aging_critical"] += 1

    account_risk_scores = []
    for acc, m in account_map.items():
        score = (m["no_shows"] * 3) + (m["rejections"] * 2) + m["aging_critical"]
        account_risk_scores.append({
            "account": acc,
            "score": score,
            "submissions": m["submissions"],
            "no_shows": m["no_shows"],
            "rejections": m["rejections"],
            "aging_critical": m["aging_critical"],
        })
    account_risk_scores.sort(key=lambda x: x["score"], reverse=True)

    # ── Recruiter stats ───────────────────────────────────────────────────
    recruiter_map: Dict[str, Dict] = defaultdict(lambda: {
        "active": 0, "no_shows": 0, "rejections": 0
    })
    for s in submissions:
        rec = s.get("recruiter_name", "Unknown")
        recruiter_map[rec]["active"] += 1
        status = s.get("canonical_status", "")
        if status == "INTERVIEW_NO_SHOW":
            recruiter_map[rec]["no_shows"] += 1
        elif "REJECTION" in status:
            recruiter_map[rec]["rejections"] += 1

    recruiter_stats = [
        {"recruiter": k, **v} for k, v in recruiter_map.items()
    ]
    recruiter_stats.sort(key=lambda x: x["active"], reverse=True)

    # ── Trend data (mock 4-week trend from current snapshot) ──────────────
    # In production this would query historical dashboard_snapshots
    trend_data = {
        "weeks": ["W-4", "W-3", "W-2", "W-1", "Current"],
        "sla_breaches": [max(0, aging_critical - 4 + i) for i in range(5)],
        "no_shows": [max(0, no_shows - 3 + i) for i in range(5)],
        "tech_rejections": [max(0, tech_rejections - 2 + i) for i in range(5)],
        "open_positions": [max(0, total_positions - 2 + i) for i in range(5)],
    }

    analytics: Dict[str, Any] = {
        "kpis": {
            "open_positions": total_positions,
            "total_submissions": total_submissions,
            "aging_critical": aging_critical,
            "aging_at_risk": aging_at_risk,
            "no_shows": no_shows,
            "budget_mismatch": budget_mismatch,
            "tech_rejections": tech_rejections,
            "on_hold": on_hold,
            "no_show_interviews": no_show_interviews,
        },
        "status_distribution": dict(status_counts),
        "account_risk_scores": account_risk_scores[:8],
        "recruiter_stats": recruiter_stats[:8],
        "trend_data": trend_data,
    }

    log.info("[analytics] kpis=%s", analytics["kpis"])

    return {
        "analytics": analytics,
        "current_node": "analytics",
        "errors": [],
    }
