"""Data Cleaning Node — normalise, validate, and structure raw TGAPDB data.

Uses the exact column names returned by the 4 production SQL queries
defined in data_fetch.py (Scheduler Summary Stack schema).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from agents.state import OpsState
from app.core.config import settings
from app.core.logging_config import get_logger

log = get_logger(__name__)

# SLA risk thresholds (days without movement = escalation signal)
_SLA_RISK_DAYS = settings.sla_aging_days         # default 5
_SLA_CRITICAL_DAYS = 30


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def _normalise_sub_status(raw: str) -> str:
    """Map TG lookup_code text → canonical operational label.

    The sub_status column in TGAPDB stores the lookup_code text value
    (e.g. 'CAN - Interview No-show', 'TECH - Rejected after Phone Interview').
    """
    s = (raw or "").lower().strip()

    if any(x in s for x in ("no-show", "no show", "noshow", "didn't show", "missed")):
        return "INTERVIEW_NO_SHOW"
    if any(x in s for x in ("out of budget", "over budget", "salary mismatch",
                              "rate mismatch", "compensation mismatch")):
        return "BUDGET_MISMATCH"
    if any(x in s for x in ("rejected", "rejection", "not selected", "declined by client")):
        return "TECH_REJECTION"
    if any(x in s for x in ("high notice", "notice period", "notice period issue",
                              "long notice")):
        return "NOTICE_PERIOD_ISSUE"
    if any(x in s for x in ("wrong profile", "profile mismatch", "wrong submission",
                              "not matching")):
        return "WRONG_PROFILE"
    if any(x in s for x in ("placed", "hired", "onboard", "joining")):
        return "PLACED"
    if any(x in s for x in ("offered", "offer released", "offer given")):
        return "OFFERED"
    if any(x in s for x in ("withdrawn", "withdraw", "backed out", "dropped out",
                              "not interested")):
        return "WITHDRAWN"
    if any(x in s for x in ("mined",)):
        return "MINED"
    if any(x in s for x in ("hold", "on hold", "paused", "deferred")):
        return "HOLD"
    if any(x in s for x in ("submitted", "pending action", "pending", "qa - submitted",
                              "sales - submitted", "am - submitted", "ai - submitted",
                              "am accpted", "am - accepted", "qam - submitted")):
        return "SUBMITTED"
    if any(x in s for x in ("cleared", "ai - cleared", "am - cleared", "shortlisted")):
        return "CLEARED"
    if any(x in s for x in ("interview", "scheduled", "confirmed", "client interview",
                              "ai - interview", "phone screen", "am - interview")):
        return "INTERVIEW_SCHEDULED"

    return "OTHER"


def _age_tag(aging_days: int) -> str:
    """SLA risk classification based on days without update."""
    if aging_days >= _SLA_CRITICAL_DAYS:
        return "CRITICAL"
    if aging_days >= _SLA_RISK_DAYS:
        return "AT_RISK"
    return "OK"


def _is_strategic_role(title: str) -> bool:
    """Detect executive/leadership-critical role from title keywords (Q7)."""
    keywords = (
        "vp ", "v.p.", "vice president", "director", "head of", "head -",
        "cto", "cfo", "coo", "cmo", "ciso", "cpo",
        "principal", "staff ", "architect", "pmo",
        "chief", "president", "gm ", "general manager",
        "partner", "managing director", "md ",
    )
    t = (title or "").lower()
    return any(k in t for k in keywords)


def data_clean_node(state: OpsState) -> dict:
    """Clean, validate, and enrich raw TGAPDB data for AI agents."""
    log.info("[data_clean] run_id=%s processing", state["run_id"])

    raw = state.get("raw_data", {})
    cleaned: Dict[str, Any] = {}

    # ── 1. Open positions ─────────────────────────────────────────────────────
    positions = raw.get("open_positions", [])
    cleaned_positions = []
    for p in positions:
        aging = _safe_int(p.get("aging_days"))
        title = str(p.get("req_title") or "")
        cleaned_positions.append({
            **p,
            "aging_days": aging,
            "aging_tag": _age_tag(aging),
            "account_name": p.get("customer") or "",
            "recruiter_name": p.get("req_recruiter_manager") or p.get("primary_recruiter_on_req") or "",
            "is_strategic": _is_strategic_role(title),
        })
    cleaned["open_positions"] = cleaned_positions

    # ── 2. Submissions ─────────────────────────────────────────────────────────
    submissions = raw.get("submissions_aging", [])
    cleaned_subs = []
    for s in submissions:
        aging = _safe_int(s.get("sub_age"))
        raw_status = str(s.get("sub_status") or "")
        cleaned_subs.append({
            **s,
            "aging_days": aging,
            "aging_tag": _age_tag(aging),
            "submission_status": raw_status,           # original text
            "canonical_status": _normalise_sub_status(raw_status),
            "account_name": s.get("customer") or "",
            "recruiter_name": s.get("sub_from") or s.get("assigned_sub_to") or "",
        })
    cleaned["submissions"] = cleaned_subs

    # ── 3. Interview breakdown ────────────────────────────────────────────────
    interviews = raw.get("interview_breakdown", [])
    cleaned_interviews = []
    for i in interviews:
        occurred = str(i.get("occurred_bucket") or "").lower()
        cleaned_interviews.append({
            **i,
            "is_past": "past" in occurred or "today" in occurred,
            "is_future": "future" in occurred or "scheduled" in occurred,
            "is_not_scheduled": "not scheduled" in occurred,
        })
    cleaned["interviews"] = cleaned_interviews

    # ── 4. Feedback by round ──────────────────────────────────────────────────
    feedback = raw.get("feedback_by_round", [])
    cleaned["feedback"] = [
        {
            **f,
            "avg_rating": float(f.get("avg_rating") or 0),
            "is_low_rated": float(f.get("avg_rating") or 0) < 2.5,
            "has_reject_signal": "reject" in str(f.get("sample_comments") or "").lower(),
            "has_hire_signal": "strong hire" in str(f.get("sample_comments") or "").lower(),
        }
        for f in feedback
    ]

    # ── Derived aggregates ────────────────────────────────────────────────────
    from collections import Counter

    status_counter = Counter(s["canonical_status"] for s in cleaned["submissions"])
    recruiter_counter = Counter(
        s.get("recruiter_name") or s.get("sub_from") or ""
        for s in cleaned["submissions"]
        if s.get("recruiter_name") or s.get("sub_from")
    )
    # Use customer field (real DB) or account_name (fixture)
    account_counter = Counter(
        s.get("customer") or s.get("account_name") or ""
        for s in cleaned["submissions"]
        if s.get("customer") or s.get("account_name")
    )

    cleaned["summary"] = {
        "total_open_positions": len(cleaned["open_positions"]),
        "total_submissions": len(cleaned["submissions"]),
        "aging_critical": sum(1 for p in cleaned["open_positions"] if p["aging_tag"] == "CRITICAL"),
        "aging_at_risk": sum(1 for p in cleaned["open_positions"] if p["aging_tag"] == "AT_RISK"),
        "strategic_roles_open": sum(1 for p in cleaned["open_positions"] if p["is_strategic"]),
        "no_show_count": status_counter.get("INTERVIEW_NO_SHOW", 0),
        "budget_mismatch_count": status_counter.get("BUDGET_MISMATCH", 0),
        "tech_rejection_count": status_counter.get("TECH_REJECTION", 0),
        "mined_count": status_counter.get("MINED", 0),
        "wrong_profile_count": status_counter.get("WRONG_PROFILE", 0),
        "notice_period_count": status_counter.get("NOTICE_PERIOD_ISSUE", 0),
        "on_hold_count": status_counter.get("HOLD", 0),
        "accounts": list(account_counter.keys()),
        "top_recruiters_by_load": recruiter_counter.most_common(5),
        "submission_status_breakdown": dict(status_counter),
    }

    log.info("[data_clean] summary=%s", cleaned["summary"])
    return {
        "cleaned_data": cleaned,
        "current_node": "data_clean",
        "errors": [],
    }
