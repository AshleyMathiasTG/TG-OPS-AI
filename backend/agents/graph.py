"""Main LangGraph orchestration graph for TG OPS AI.

Flow:
  data_fetch → data_clean → executive_summary → risk_detection
    → analytics → decision_router → action_recommendation
    → approval → notification → persistence
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from langgraph.graph import END, START, StateGraph

from agents.state import OpsState
from agents.nodes.data_fetch import data_fetch_node
from agents.nodes.data_clean import data_clean_node
from agents.nodes.executive_summary import executive_summary_node
from agents.nodes.risk_detection import risk_detection_node
from agents.nodes.analytics import analytics_node
from agents.nodes.decision_router import decision_router_node
from agents.nodes.action_recommendation import action_recommendation_node
from agents.nodes.approval import approval_node
from agents.nodes.notification import notification_node
from agents.nodes.persistence import persistence_node
from app.core.logging_config import get_logger

log = get_logger(__name__)


def build_graph() -> StateGraph:
    """Assemble and compile the TG OPS AI LangGraph workflow."""
    graph = StateGraph(OpsState)

    # ── Register nodes ───────────────────────────────────────────────────
    graph.add_node("data_fetch", data_fetch_node)
    graph.add_node("data_clean", data_clean_node)
    graph.add_node("executive_summary", executive_summary_node)
    graph.add_node("risk_detection", risk_detection_node)
    graph.add_node("analytics", analytics_node)
    graph.add_node("decision_router", decision_router_node)
    graph.add_node("action_recommendation", action_recommendation_node)
    graph.add_node("approval", approval_node)
    graph.add_node("notification", notification_node)
    graph.add_node("persistence", persistence_node)

    # ── Wire edges ───────────────────────────────────────────────────────
    graph.add_edge(START, "data_fetch")
    graph.add_edge("data_fetch", "data_clean")
    graph.add_edge("data_clean", "executive_summary")
    graph.add_edge("executive_summary", "risk_detection")
    graph.add_edge("risk_detection", "analytics")
    graph.add_edge("analytics", "decision_router")
    graph.add_edge("decision_router", "action_recommendation")
    graph.add_edge("action_recommendation", "approval")
    graph.add_edge("approval", "notification")
    graph.add_edge("notification", "persistence")
    graph.add_edge("persistence", END)

    return graph.compile()


# Compiled graph singleton
compiled_graph = build_graph()


async def run_pipeline(triggered_by: str = "scheduler") -> dict:
    """Execute the full TG OPS AI pipeline and return the final state."""
    run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    log.info("=== TG OPS AI Pipeline START run_id=%s triggered_by=%s ===", run_id, triggered_by)

    initial_state: OpsState = {
        "run_id": run_id,
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "raw_data": {},
        "cleaned_data": {},
        "executive_summary": "",
        "executive_highlights": [],
        "risk_events": [],
        "sla_events": [],
        "analytics": {},
        "issues_above_threshold": [],
        "issues_below_threshold": [],
        "recommendations": [],
        "approval_requests": [],
        "notifications": [],
        "errors": [],
        "current_node": "start",
    }

    final_state = await compiled_graph.ainvoke(initial_state)

    log.info(
        "=== TG OPS AI Pipeline DONE run_id=%s risks=%d sla=%d approvals=%d ===",
        run_id,
        len(final_state.get("risk_events", [])),
        len(final_state.get("sla_events", [])),
        len(final_state.get("approval_requests", [])),
    )

    return final_state
