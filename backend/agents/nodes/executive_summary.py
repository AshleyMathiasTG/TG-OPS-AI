"""Executive Summary Agent — generates concise operational highlights using LLM."""
from __future__ import annotations

import json
from typing import List

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from agents.state import OpsState
from app.core.config import settings
from app.core.logging_config import get_logger

log = get_logger(__name__)

_SYSTEM_PROMPT = """You are TG OPS AI — a senior operational intelligence analyst for a recruitment firm.

Your job: produce a SHORT executive briefing (max 8 bullet points) from the operational data snapshot.

Rules:
- Each bullet must be ≤15 words
- Be specific: include names, numbers, account names
- Prioritise critical and high-severity items
- Do NOT explain methodology or add filler text
- Format: JSON with keys "summary" (string, 1-2 sentences) and "highlights" (array of strings)

Good examples:
- "3 consecutive interview no-shows detected in Sephora AI Engineer pipeline"
- "Penumbra QA Lead aging 32 days — deadline already passed"  
- "Budget mismatch spikes in MARVELL DevOps roles"
- "Alice Chen's queue overloaded: 4 active submissions at risk"
"""


def executive_summary_node(state: OpsState) -> dict:
    """Call LLM to produce executive summary from cleaned data."""
    log.info("[exec_summary] run_id=%s", state["run_id"])

    cleaned = state.get("cleaned_data", {})
    summary_data = cleaned.get("summary", {})
    positions = cleaned.get("open_positions", [])[:8]
    submissions = cleaned.get("submissions", [])[:8]

    data_snapshot = {
        "kpi_summary": summary_data,
        "top_aging_positions": [
            {"req": p["req_title"], "account": p["account_name"],
             "days": p["aging_days"], "tag": p["aging_tag"]}
            for p in sorted(positions, key=lambda x: x["aging_days"], reverse=True)[:5]
        ],
        "top_at_risk_submissions": [
            {"candidate": s["candidate_name"], "status": s["submission_status"],
             "account": s["account_name"], "days": s["aging_days"]}
            for s in sorted(submissions, key=lambda x: x["aging_days"], reverse=True)[:5]
        ],
    }

    try:
        llm = ChatOpenAI(
            model=settings.format_model,
            api_key=settings.openai_api_key,
            temperature=0.3,
            max_retries=3,
        )
        response = llm.invoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=f"Operational data:\n{json.dumps(data_snapshot, indent=2)}"),
        ])

        text = response.content.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        parsed = json.loads(text)
        summary = parsed.get("summary", "Operational analysis complete.")
        highlights: List[str] = parsed.get("highlights", [])

    except json.JSONDecodeError:
        summary = response.content[:300] if "response" in dir() else "Analysis unavailable."
        highlights = []
    except Exception as exc:
        log.warning("[exec_summary] LLM call failed (%s) — using heuristic fallback", exc)
        summary, highlights = _heuristic_summary(summary_data)

    log.info("[exec_summary] summary=%r highlights=%d", summary[:80], len(highlights))
    return {
        "executive_summary": summary,
        "executive_highlights": highlights,
        "current_node": "executive_summary",
        "errors": [],
    }


def _heuristic_summary(data: dict) -> tuple[str, List[str]]:
    highlights = []
    if data.get("aging_critical", 0):
        highlights.append(f"{data['aging_critical']} positions critically aged (>30 days)")
    if data.get("no_show_count", 0):
        highlights.append(f"{data['no_show_count']} interview no-shows detected")
    if data.get("budget_mismatch_count", 0):
        highlights.append(f"{data['budget_mismatch_count']} budget mismatch cases")
    if data.get("tech_rejection_count", 0):
        highlights.append(f"{data['tech_rejection_count']} technical rejections this cycle")
    summary = f"Pipeline reviewed: {data.get('total_open_positions', 0)} open positions, {data.get('total_submissions', 0)} active submissions."
    return summary, highlights
