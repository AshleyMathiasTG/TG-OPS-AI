"""Action Recommendation Agent — generates AI recommendations for repeated issues."""
from __future__ import annotations

import json
import uuid
from typing import List

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from agents.state import IssueDetection, OpsState, RecommendationItem
from app.core.config import settings
from app.core.logging_config import get_logger

log = get_logger(__name__)

_SYSTEM_PROMPT = """You are TG OPS AI — Recommendation Engine.

A repeated operational issue has been detected (3+ consecutive occurrences).
Generate a precise, actionable recommendation for operations leadership.

Return ONLY a JSON object:
{
  "recommendation_text": "<40 words max — concrete action>",
  "escalation_path": "<who to escalate to and how>",
  "mitigation_steps": "<3 bullet steps, pipe-separated>",
  "confidence_score": 0.0-1.0,
  "impact_level": "LOW|MEDIUM|HIGH|CRITICAL"
}

Examples of good recommendations:
- "Reassign top 3 Penumbra candidates to Bob Kumar's colleague; add JD review with hiring manager"
- "Implement budget pre-screening call before scheduling interviews for MARVELL roles"
- "Escalate Alice Chen's overload to TA Lead; redistribute 2 Sephora reqs to David Lee"
"""


def _generate_recommendation(issue: IssueDetection, model: str, api_key: str) -> RecommendationItem:
    try:
        llm = ChatOpenAI(model=model, api_key=api_key, temperature=0.4, max_retries=3)
        payload = {
            "issue_type": issue["issue_type"],
            "title": issue["title"],
            "entity_name": issue["entity_name"],
            "account_name": issue["account_name"],
            "occurrence_count": issue["occurrence_count"],
            "description": issue["description"],
        }
        response = llm.invoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=f"Issue:\n{json.dumps(payload, indent=2)}"),
        ])
        text = response.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        parsed = json.loads(text)
        return RecommendationItem(
            issue_key=issue["issue_key"],
            issue_summary=issue["title"],
            recommendation_text=parsed.get("recommendation_text", "Review and escalate to TA Lead."),
            escalation_path=parsed.get("escalation_path", "TA Lead → Delivery Head"),
            mitigation_steps=parsed.get("mitigation_steps", "1. Review | 2. Reassign | 3. Monitor"),
            confidence_score=float(parsed.get("confidence_score", 0.75)),
            impact_level=parsed.get("impact_level", "HIGH"),
            model_used=model,
        )
    except Exception as exc:
        log.warning("[recommendation] LLM failed for %s: %s", issue["issue_key"][:16], exc)
        return _fallback_recommendation(issue, model)


def _fallback_recommendation(issue: IssueDetection, model: str) -> RecommendationItem:
    templates = {
        "INTERVIEW_NO_SHOW": "Implement pre-interview confirmation call 24h before; flag candidate for reliability review.",
        "TECH_REJECTION": "Schedule JD calibration with hiring manager; review technical bar expectations with panel.",
        "BUDGET_MISMATCH": "Add budget pre-screening before profile submission; align recruiter expectations.",
        "AGING_SUBMISSION": "Escalate to TA Lead; review if req is still active or needs priority boost.",
        "RECRUITER_OVERLOAD": "Redistribute 2-3 oldest submissions to available recruiter; review capacity.",
    }
    escalation = {
        "INTERVIEW_NO_SHOW": "Recruiter → TA Lead → Delivery Manager",
        "TECH_REJECTION": "Recruiter → Hiring Manager → TA Lead",
        "BUDGET_MISMATCH": "Recruiter → Account Manager → Finance",
        "AGING_SUBMISSION": "TA Lead → Delivery Head",
        "RECRUITER_OVERLOAD": "TA Lead → HR Head",
    }
    return RecommendationItem(
        issue_key=issue["issue_key"],
        issue_summary=issue["title"],
        recommendation_text=templates.get(issue["issue_type"], "Escalate to operations team for review."),
        escalation_path=escalation.get(issue["issue_type"], "TA Lead"),
        mitigation_steps="1. Acknowledge | 2. Reassign or recalibrate | 3. Monitor for 1 week",
        confidence_score=0.70,
        impact_level=issue.get("severity", "WARNING").replace("WARNING", "MEDIUM").replace("CRITICAL", "HIGH"),
        model_used=model,
    )


def action_recommendation_node(state: OpsState) -> dict:
    """Generate recommendations for issues that exceeded the threshold."""
    log.info("[recommendation] run_id=%s", state["run_id"])

    issues = state.get("issues_above_threshold", [])
    if not issues:
        log.info("[recommendation] No issues above threshold — skipping")
        return {
            "recommendations": [],
            "current_node": "action_recommendation",
            "errors": [],
        }

    model = settings.analytics_model
    api_key = settings.openai_api_key
    recommendations: List[RecommendationItem] = []

    for issue in issues:
        rec = _generate_recommendation(issue, model, api_key)
        recommendations.append(rec)
        log.info("[recommendation] Generated for %s (confidence=%.2f)", issue["issue_key"][:16], rec["confidence_score"])

    return {
        "recommendations": recommendations,
        "current_node": "action_recommendation",
        "errors": [],
    }
