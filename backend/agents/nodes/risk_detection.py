"""Risk & SLA Detection Agent — identifies operational risks and SLA breaches."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from agents.state import IssueDetection, OpsState
from app.core.config import settings
from app.core.logging_config import get_logger

log = get_logger(__name__)

_SYSTEM_PROMPT = """You are the TG OPS AI Risk Detection Engine.

Analyse recruitment operational data and identify concrete risks.

Return ONLY a JSON array of risk objects. Each object:
{
  "issue_type": "INTERVIEW_NO_SHOW|TECH_REJECTION|BUDGET_MISMATCH|AGING_SUBMISSION|RECRUITER_OVERLOAD|CLIENT_RISK|PIPELINE_STAGNATION|INACTIVE_REQ",
  "title": "<15 words max>",
  "severity": "INFO|WARNING|CRITICAL",
  "entity_name": "person or req or account name",
  "account_name": "account/client name",
  "description": "<25 words max — factual>"
}

Rules:
- Only flag real patterns visible in the data
- CRITICAL = immediate action needed
- WARNING = trending bad
- INFO = watch list
- Return [] if no risks found
"""


def _make_issue_key(issue_type: str, entity: str, account: str) -> str:
    raw = f"{issue_type}::{entity}::{account}".lower()
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _heuristic_risks(cleaned: Dict[str, Any]) -> List[IssueDetection]:
    """Fast rule-based risk detection as fallback when LLM unavailable."""
    issues: List[IssueDetection] = []
    sla_days = settings.sla_aging_days

    # Aging positions
    for pos in cleaned.get("open_positions", []):
        days = pos.get("aging_days", 0)
        if days >= 30:
            issues.append(IssueDetection(
                issue_key=_make_issue_key("AGING_SUBMISSION", pos["req_id"], pos["account_name"]),
                issue_type="AGING_SUBMISSION",
                title=f"{pos['req_title']} aging {days} days — critical",
                severity="CRITICAL",
                entity_name=pos["req_title"],
                account_name=pos["account_name"],
                occurrence_count=1,
                description=f"Position at {pos['account_name']} has been open {days} days without fill.",
                metadata={"req_id": pos.get("req_id"), "aging_days": days},
            ))
        elif days >= sla_days:
            issues.append(IssueDetection(
                issue_key=_make_issue_key("AGING_SUBMISSION", pos["req_id"], pos["account_name"]),
                issue_type="AGING_SUBMISSION",
                title=f"{pos['req_title']} at SLA risk ({days} days)",
                severity="WARNING",
                entity_name=pos["req_title"],
                account_name=pos["account_name"],
                occurrence_count=1,
                description=f"Position approaching SLA threshold at {pos['account_name']}.",
                metadata={"req_id": pos.get("req_id"), "aging_days": days},
            ))

    # No-shows
    no_shows = [s for s in cleaned.get("submissions", []) if s.get("canonical_status") == "INTERVIEW_NO_SHOW"]
    for s in no_shows:
        issues.append(IssueDetection(
            issue_key=_make_issue_key("INTERVIEW_NO_SHOW", s["candidate_name"], s["account_name"]),
            issue_type="INTERVIEW_NO_SHOW",
            title=f"Interview no-show: {s['candidate_name']} ({s['account_name']})",
            severity="WARNING",
            entity_name=s["candidate_name"],
            account_name=s["account_name"],
            occurrence_count=1,
            description=f"Candidate {s['candidate_name']} missed interview for {s.get('req_title', 'unknown role')}.",
            metadata={"submission_id": s.get("submission_id"), "recruiter": s.get("recruiter_name")},
        ))

    # Budget mismatches
    budget = [s for s in cleaned.get("submissions", []) if s.get("canonical_status") == "BUDGET_MISMATCH"]
    for s in budget:
        issues.append(IssueDetection(
            issue_key=_make_issue_key("BUDGET_MISMATCH", s["account_name"], s.get("req_id", "")),
            issue_type="BUDGET_MISMATCH",
            title=f"Budget mismatch: {s['account_name']} — {s.get('req_title', '')}",
            severity="WARNING",
            entity_name=s.get("req_title", ""),
            account_name=s["account_name"],
            occurrence_count=1,
            description=f"Candidate {s['candidate_name']} exceeds budget for {s['account_name']}.",
            metadata={"submission_id": s.get("submission_id")},
        ))

    # Tech rejections
    tech_rej = [s for s in cleaned.get("submissions", []) if s.get("canonical_status") == "TECH_REJECTION"]
    for s in tech_rej:
        issues.append(IssueDetection(
            issue_key=_make_issue_key("TECH_REJECTION", s["account_name"], s.get("recruiter_name", "")),
            issue_type="TECH_REJECTION",
            title=f"Tech rejection: {s['account_name']} ({s.get('recruiter_name', '')})",
            severity="WARNING",
            entity_name=s["account_name"],
            account_name=s["account_name"],
            occurrence_count=1,
            description=f"Candidate {s['candidate_name']} rejected post phone interview at {s['account_name']}.",
            metadata={"recruiter": s.get("recruiter_name")},
        ))

    # Recruiter load check
    from collections import Counter
    rec_counts = Counter(s.get("recruiter_name") for s in cleaned.get("submissions", []) if s.get("recruiter_name"))
    for recruiter, count in rec_counts.items():
        if count >= 4:
            issues.append(IssueDetection(
                issue_key=_make_issue_key("RECRUITER_OVERLOAD", recruiter, ""),
                issue_type="RECRUITER_OVERLOAD",
                title=f"Recruiter overload: {recruiter} ({count} active submissions)",
                severity="WARNING",
                entity_name=recruiter,
                account_name="",
                occurrence_count=1,
                description=f"{recruiter} managing {count} active submissions simultaneously.",
                metadata={"count": count},
            ))

    return issues


def risk_detection_node(state: OpsState) -> dict:
    """Detect operational risks using LLM + heuristic fallback."""
    log.info("[risk_detection] run_id=%s", state["run_id"])

    cleaned = state.get("cleaned_data", {})
    summary = cleaned.get("summary", {})

    data_payload = {
        "summary": summary,
        "submissions_sample": cleaned.get("submissions", [])[:10],
        "positions_sample": [
            {"req_title": p["req_title"], "account": p["account_name"],
             "aging_days": p["aging_days"], "tag": p["aging_tag"]}
            for p in cleaned.get("open_positions", [])[:10]
        ],
        "rejections": cleaned.get("rejections", [])[:10],
    }

    risk_issues: List[IssueDetection] = []
    sla_issues: List[IssueDetection] = []

    try:
        llm = ChatOpenAI(
            model=settings.risk_model,
            api_key=settings.openai_api_key,
            temperature=0.1,
            max_retries=3,
        )
        response = llm.invoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=f"Data:\n{json.dumps(data_payload, indent=2)}"),
        ])
        text = response.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        raw_risks = json.loads(text)

        for r in raw_risks:
            item = IssueDetection(
                issue_key=_make_issue_key(r["issue_type"], r.get("entity_name", ""), r.get("account_name", "")),
                issue_type=r["issue_type"],
                title=r["title"],
                severity=r.get("severity", "WARNING"),
                entity_name=r.get("entity_name", ""),
                account_name=r.get("account_name", ""),
                occurrence_count=1,
                description=r.get("description", ""),
                metadata={},
            )
            if "SLA" in r["issue_type"] or "AGING" in r["issue_type"]:
                sla_issues.append(item)
            else:
                risk_issues.append(item)

        log.info("[risk_detection] LLM detected %d risks, %d sla", len(risk_issues), len(sla_issues))

    except Exception as exc:
        log.warning("[risk_detection] LLM failed (%s) — using heuristic", exc)
        all_issues = _heuristic_risks(cleaned)
        sla_types = {"AGING_SUBMISSION"}
        sla_issues = [i for i in all_issues if i["issue_type"] in sla_types]
        risk_issues = [i for i in all_issues if i["issue_type"] not in sla_types]
        log.info("[risk_detection] Heuristic: %d risks, %d sla", len(risk_issues), len(sla_issues))

    return {
        "risk_events": risk_issues,
        "sla_events": sla_issues,
        "current_node": "risk_detection",
        "errors": [],
    }
