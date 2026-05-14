"""Data Fetch Node — pulls data from TG Database (or fixtures).

SQL queries are derived from the Scheduler Summary Stack specification
and use the actual TGAPDB schema:
  mst_requirements, adm_can_submissions, adm_interview_panel,
  adm_interviewers, adm_can_interview_fb_details,
  adm_can_submission_interview_summary, mst_organizations,
  mst_candidates, adm_users, adm_lookup_codes

ALL queries are SELECT-only. The tg_database layer enforces this
with a read-only transaction as a second line of defence.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from agents.state import OpsState
from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.tg_database import tg_db

log = get_logger(__name__)


# ── Production SQL queries (exact TGAPDB schema) ──────────────────────────────

# Q1 — Open positions (active in the rolling window)
# Shows positions that are currently OPEN/APPROVED and either opened OR had close_by_date
# within the last %(window)s days, so long-aging critical reqs are always included.
_SQL_OPEN_POSITIONS = """
SELECT
    r.req_id,
    r.client_req_name                       AS req_title,
    lc_req.lookup_code                      AS req_status,
    r.open_date,
    r.close_by_date                         AS deadline_to_close_position,
    DATEDIFF(CURDATE(), r.open_date)        AS aging_days,
    r.openings                              AS openings_count,
    o.organization_name                     AS customer,
    u_rm.user_name                          AS req_recruiter_manager,
    u_pr.user_name                          AS primary_recruiter_on_req,
    CASE
        WHEN r.bill_type = 1 THEN 'Billable T&M'
        WHEN r.bill_type = 2 THEN 'Billable FB/MS'
        ELSE 'Non - Billable'
    END                                     AS billable_type
FROM mst_requirements r
JOIN adm_lookup_codes lc_req
    ON lc_req.lookup_code_id = r.req_status_id
LEFT JOIN mst_organizations o
    ON o.organization_id = r.organization_id
LEFT JOIN adm_users u_rm
    ON u_rm.user_id = r.recruiter_manager
LEFT JOIN mst_req_recruiters rr
    ON rr.req_id = r.req_id
    AND rr.primary_flag = 'Y'
    AND (rr.end_date IS NULL OR rr.end_date >= CURDATE())
LEFT JOIN adm_users u_pr
    ON u_pr.user_id = rr.recruiter_id
WHERE lc_req.lookup_code IN ('OPEN', 'APPROVED')
  AND (
      r.open_date      >= DATE_SUB(CURDATE(), INTERVAL %(window)s DAY)
   OR r.close_by_date  >= DATE_SUB(CURDATE(), INTERVAL %(window)s DAY)
   OR r.close_by_date  IS NULL
  )
ORDER BY r.close_by_date ASC, r.open_date ASC
LIMIT %(limit)s
"""

# Q2 — Submissions updated within the rolling window
# Detects: stalled candidates, recruiter overload, SLA aging
_SQL_SUBMISSIONS_AGING = """
SELECT
    s.submission_id                         AS sub_id,
    r.client_req_name                       AS req_name,
    o.organization_name                     AS customer,
    c.full_name                             AS candidate_name,
    lc_sub.lookup_code                      AS sub_status,
    DATEDIFF(CURDATE(), s.last_update_date) AS sub_age,
    u_to.user_name                          AS assigned_sub_to,
    s.sub_feedback                          AS sub_feedback,
    u_from.user_name                        AS sub_from,
    s.last_update_date,
    s.creation_date,
    r.close_by_date                         AS position_close_deadline,
    lc_req.lookup_code                      AS requirement_status,
    u_rm.user_name                          AS req_recruiter_manager,
    CASE
        WHEN r.bill_type = 1 THEN 'Billable T&M'
        WHEN r.bill_type = 2 THEN 'Billable FB/MS'
        ELSE 'Non - Billable'
    END                                     AS billable_type
FROM adm_can_submissions s
JOIN mst_requirements r
    ON r.req_id = s.req_id
LEFT JOIN mst_organizations o
    ON o.organization_id = r.organization_id
LEFT JOIN adm_lookup_codes lc_req
    ON lc_req.lookup_code_id = r.req_status_id
LEFT JOIN adm_lookup_codes lc_sub
    ON lc_sub.lookup_code_id = s.sub_status
LEFT JOIN mst_candidates c
    ON c.candidate_id = s.candidate_id
LEFT JOIN adm_users u_to
    ON u_to.user_id = s.sub_to
LEFT JOIN adm_users u_from
    ON u_from.user_id = s.sub_from
LEFT JOIN adm_users u_rm
    ON u_rm.user_id = r.recruiter_manager
WHERE s.last_update_date >= DATE_SUB(CURDATE(), INTERVAL %(window)s DAY)
ORDER BY s.last_update_date ASC
LIMIT %(limit)s
"""

# Q3 — Interviews within the rolling window
# Detects: scheduled vs completed, panel assignments, no-show indicators
_SQL_INTERVIEW_BREAKDOWN = """
SELECT
    p.interviewer_id,
    p.submission_id,
    p.interview_date,
    p.active_flag,
    CASE
        WHEN p.interview_date IS NULL             THEN 'Not scheduled'
        WHEN DATE(p.interview_date) < CURDATE()   THEN 'Completed (past)'
        WHEN DATE(p.interview_date) = CURDATE()   THEN 'Today'
        ELSE                                           'Scheduled (future)'
    END                                         AS occurred_bucket,
    c.full_name                                 AS candidate_name,
    r.client_req_name                           AS req_title,
    u_from.user_name                            AS recruiter,
    u_panel.user_name                           AS panel_user
FROM adm_interview_panel p
LEFT JOIN adm_can_submissions s
    ON s.submission_id = p.submission_id
LEFT JOIN mst_requirements r
    ON r.req_id = s.req_id
LEFT JOIN mst_candidates c
    ON c.candidate_id = s.candidate_id
LEFT JOIN adm_users u_from
    ON u_from.user_id = s.sub_from
LEFT JOIN adm_users u_panel
    ON u_panel.user_id = p.user_id
WHERE p.interview_date >= DATE_SUB(CURDATE(), INTERVAL %(window)s DAY)
   OR p.interview_date IS NULL
ORDER BY p.interview_date DESC, p.interviewer_id DESC
LIMIT %(limit)s
"""

# Q4 — Interview feedback within the rolling window
# Detects: low-rating patterns, recurring rejection signals
_SQL_FEEDBACK_BY_ROUND = """
SELECT
    fb.submission_id,
    fb.interview_id,
    p.interview_date,
    ROUND(AVG(fb.rating), 2)               AS avg_rating,
    COUNT(*)                                AS feedback_line_count,
    LEFT(
        GROUP_CONCAT(
            DISTINCT fb.comment
            ORDER BY fb.id
            SEPARATOR ' | '
        ),
        500
    )                                       AS sample_comments
FROM adm_can_interview_fb_details fb
LEFT JOIN adm_interview_panel p
    ON p.interviewer_id = fb.interview_id
WHERE p.interview_date >= DATE_SUB(CURDATE(), INTERVAL %(window)s DAY)
   OR p.interview_date IS NULL
GROUP BY
    fb.submission_id,
    fb.interview_id,
    p.interview_date
ORDER BY fb.submission_id, p.interview_date
LIMIT %(limit)s
"""

_QUERIES: Dict[str, str] = {
    "open_positions":       _SQL_OPEN_POSITIONS,
    "submissions_aging":    _SQL_SUBMISSIONS_AGING,
    "interview_breakdown":  _SQL_INTERVIEW_BREAKDOWN,
    "feedback_by_round":    _SQL_FEEDBACK_BY_ROUND,
}


# ── Fixture data (used when TGAP_FIXTURE_ONLY=1 / no VPN) ────────────────────

def _build_fixture_data() -> Dict[str, Any]:
    """Rich fixture dataset matching real TGAPDB column names."""
    return {
        "open_positions": [
            {"req_id": 1001, "req_title": "Senior AI Engineer", "req_status": "OPEN",
             "open_date": "2026-04-26", "deadline_to_close_position": "2026-05-30",
             "aging_days": 18, "openings_count": 2, "customer": "Sephora",
             "req_recruiter_manager": "Alice.Chen", "primary_recruiter_on_req": "Alice.Chen",
             "billable_type": "Billable T&M"},
            {"req_id": 1002, "req_title": "QA Lead", "req_status": "OPEN",
             "open_date": "2026-04-12", "deadline_to_close_position": "2026-05-15",
             "aging_days": 32, "openings_count": 1, "customer": "Penumbra",
             "req_recruiter_manager": "Bob.Kumar", "primary_recruiter_on_req": "Bob.Kumar",
             "billable_type": "Billable T&M"},
            {"req_id": 1003, "req_title": "DevOps Engineer", "req_status": "APPROVED",
             "open_date": "2026-05-05", "deadline_to_close_position": "2026-05-25",
             "aging_days": 9, "openings_count": 1, "customer": "MARVELL",
             "req_recruiter_manager": "Carol.Singh", "primary_recruiter_on_req": "Carol.Singh",
             "billable_type": "Billable T&M"},
            {"req_id": 1004, "req_title": "Data Scientist", "req_status": "OPEN",
             "open_date": "2026-04-30", "deadline_to_close_position": "2026-06-01",
             "aging_days": 14, "openings_count": 1, "customer": "MARVELL",
             "req_recruiter_manager": "Alice.Chen", "primary_recruiter_on_req": "Alice.Chen",
             "billable_type": "Non - Billable"},
            {"req_id": 1005, "req_title": "ML Engineer", "req_status": "OPEN",
             "open_date": "2026-04-23", "deadline_to_close_position": "2026-05-20",
             "aging_days": 21, "openings_count": 1, "customer": "Sephora",
             "req_recruiter_manager": "Alice.Chen", "primary_recruiter_on_req": "Alice.Chen",
             "billable_type": "Billable T&M"},
            {"req_id": 1006, "req_title": "Backend Engineer", "req_status": "OPEN",
             "open_date": "2026-03-30", "deadline_to_close_position": "2026-04-30",
             "aging_days": 45, "openings_count": 1, "customer": "Penumbra",
             "req_recruiter_manager": "Bob.Kumar", "primary_recruiter_on_req": "Bob.Kumar",
             "billable_type": "Billable T&M"},
            {"req_id": 1007, "req_title": "Cloud Architect", "req_status": "APPROVED",
             "open_date": "2026-05-08", "deadline_to_close_position": "2026-05-28",
             "aging_days": 6, "openings_count": 1, "customer": "GlobalBank",
             "req_recruiter_manager": "Eve.Thomas", "primary_recruiter_on_req": "Eve.Thomas",
             "billable_type": "Billable T&M"},
            {"req_id": 1008, "req_title": "VP of Engineering", "req_status": "OPEN",
             "open_date": "2026-04-01", "deadline_to_close_position": "2026-05-31",
             "aging_days": 43, "openings_count": 1, "customer": "Sephora",
             "req_recruiter_manager": "Alice.Chen", "primary_recruiter_on_req": "David.Lee",
             "billable_type": "Billable T&M"},
        ],
        "submissions_aging": [
            {"sub_id": "S001", "req_name": "Senior AI Engineer", "customer": "Sephora",
             "candidate_name": "John Doe", "sub_status": "CAN - Interview No-show",
             "sub_age": 12, "assigned_sub_to": "Alice.Chen", "sub_from": "Alice.Chen",
             "sub_feedback": "", "last_update_date": "2026-05-02",
             "requirement_status": "OPEN", "req_recruiter_manager": "Alice.Chen",
             "billable_type": "Billable T&M", "position_close_deadline": "2026-05-30"},
            {"sub_id": "S002", "req_name": "QA Lead", "customer": "Penumbra",
             "candidate_name": "Jane Smith", "sub_status": "TECH - Rejected after Phone Interview",
             "sub_age": 28, "assigned_sub_to": "Bob.Kumar", "sub_from": "Bob.Kumar",
             "sub_feedback": "Did not meet technical bar", "last_update_date": "2026-04-16",
             "requirement_status": "OPEN", "req_recruiter_manager": "Bob.Kumar",
             "billable_type": "Billable T&M", "position_close_deadline": "2026-05-15"},
            {"sub_id": "S003", "req_name": "QA Lead", "customer": "Penumbra",
             "candidate_name": "Mike Johnson", "sub_status": "QA - Candidate out of Budget",
             "sub_age": 15, "assigned_sub_to": "Bob.Kumar", "sub_from": "Bob.Kumar",
             "sub_feedback": "Expected 30% above budget", "last_update_date": "2026-04-29",
             "requirement_status": "OPEN", "req_recruiter_manager": "Bob.Kumar",
             "billable_type": "Billable T&M", "position_close_deadline": "2026-05-15"},
            {"sub_id": "S004", "req_name": "DevOps Engineer", "customer": "MARVELL",
             "candidate_name": "Sara Wilson", "sub_status": "QA - Submitted and Pending Action",
             "sub_age": 5, "assigned_sub_to": "Carol.Singh", "sub_from": "Carol.Singh",
             "sub_feedback": "Strong profile", "last_update_date": "2026-05-09",
             "requirement_status": "APPROVED", "req_recruiter_manager": "Carol.Singh",
             "billable_type": "Billable T&M", "position_close_deadline": "2026-05-25"},
            {"sub_id": "S005", "req_name": "ML Engineer", "customer": "Sephora",
             "candidate_name": "Tom Brown", "sub_status": "CAN - Interview No-show",
             "sub_age": 19, "assigned_sub_to": "Alice.Chen", "sub_from": "Alice.Chen",
             "sub_feedback": "", "last_update_date": "2026-04-25",
             "requirement_status": "OPEN", "req_recruiter_manager": "Alice.Chen",
             "billable_type": "Billable T&M", "position_close_deadline": "2026-05-20"},
            {"sub_id": "S006", "req_name": "Backend Engineer", "customer": "Penumbra",
             "candidate_name": "Lisa Park", "sub_status": "MINED",
             "sub_age": 43, "assigned_sub_to": "Bob.Kumar", "sub_from": "Bob.Kumar",
             "sub_feedback": "On hold per client", "last_update_date": "2026-04-01",
             "requirement_status": "OPEN", "req_recruiter_manager": "Bob.Kumar",
             "billable_type": "Billable T&M", "position_close_deadline": "2026-04-30"},
            {"sub_id": "S007", "req_name": "Senior AI Engineer", "customer": "Sephora",
             "candidate_name": "Ryan Zhang", "sub_status": "CAN - Interview No-show",
             "sub_age": 8, "assigned_sub_to": "Alice.Chen", "sub_from": "Alice.Chen",
             "sub_feedback": "", "last_update_date": "2026-05-06",
             "requirement_status": "OPEN", "req_recruiter_manager": "Alice.Chen",
             "billable_type": "Billable T&M", "position_close_deadline": "2026-05-30"},
            {"sub_id": "S008", "req_name": "DevOps Engineer", "customer": "MARVELL",
             "candidate_name": "Amy Davis", "sub_status": "QA - Candidate out of Budget",
             "sub_age": 7, "assigned_sub_to": "Carol.Singh", "sub_from": "Carol.Singh",
             "sub_feedback": "Budget gap $30k", "last_update_date": "2026-05-07",
             "requirement_status": "APPROVED", "req_recruiter_manager": "Carol.Singh",
             "billable_type": "Non - Billable", "position_close_deadline": "2026-05-25"},
            {"sub_id": "S009", "req_name": "Backend Engineer", "customer": "Penumbra",
             "candidate_name": "Chris Rao", "sub_status": "TECH - Rejected after Phone Interview",
             "sub_age": 56, "assigned_sub_to": "Bob.Kumar", "sub_from": "Bob.Kumar",
             "sub_feedback": "Communication gap", "last_update_date": "2026-03-19",
             "requirement_status": "OPEN", "req_recruiter_manager": "Bob.Kumar",
             "billable_type": "Billable T&M", "position_close_deadline": "2026-04-30"},
            {"sub_id": "S010", "req_name": "VP of Engineering", "customer": "Sephora",
             "candidate_name": "Priya Nair", "sub_status": "MINED",
             "sub_age": 47, "assigned_sub_to": "David.Lee", "sub_from": "Alice.Chen",
             "sub_feedback": "Candidate exploring options", "last_update_date": "2026-03-28",
             "requirement_status": "OPEN", "req_recruiter_manager": "Alice.Chen",
             "billable_type": "Billable T&M", "position_close_deadline": "2026-05-31"},
        ],
        "interview_breakdown": [
            {"submission_id": "S001", "req_id": 1001, "client_req_name": "Senior AI Engineer",
             "candidate_name": "John Doe", "interview_round": "Phone Screen",
             "interview_mode": "Phone", "panel_user": "Alice.Chen",
             "interview_date": "2026-05-10", "occurred_bucket": "Completed (past)",
             "customer": "Sephora", "recruiter": "Alice.Chen"},
            {"submission_id": "S005", "req_id": 1005, "client_req_name": "ML Engineer",
             "candidate_name": "Tom Brown", "interview_round": "Phone Screen",
             "interview_mode": "Phone", "panel_user": "Alice.Chen",
             "interview_date": "2026-05-08", "occurred_bucket": "Completed (past)",
             "customer": "Sephora", "recruiter": "Alice.Chen"},
            {"submission_id": "S007", "req_id": 1001, "client_req_name": "Senior AI Engineer",
             "candidate_name": "Ryan Zhang", "interview_round": "Phone Screen",
             "interview_mode": "Phone", "panel_user": "Alice.Chen",
             "interview_date": "2026-05-12", "occurred_bucket": "Completed (past)",
             "customer": "Sephora", "recruiter": "Alice.Chen"},
            {"submission_id": "S002", "req_id": 1002, "client_req_name": "QA Lead",
             "candidate_name": "Jane Smith", "interview_round": "Technical Interview",
             "interview_mode": "Video", "panel_user": "Bob.Kumar",
             "interview_date": "2026-04-20", "occurred_bucket": "Completed (past)",
             "customer": "Penumbra", "recruiter": "Bob.Kumar"},
            {"submission_id": "S004", "req_id": 1003, "client_req_name": "DevOps Engineer",
             "candidate_name": "Sara Wilson", "interview_round": "Technical Interview",
             "interview_mode": "Video", "panel_user": "Carol.Singh",
             "interview_date": "2026-05-18", "occurred_bucket": "Scheduled (future)",
             "customer": "MARVELL", "recruiter": "Carol.Singh"},
        ],
        "feedback_by_round": [
            {"submission_id": "S002", "interview_round": "Technical Interview",
             "interview_date": "2026-04-20", "avg_rating": 1.5,
             "feedback_line_count": 3, "sample_comments": "Poor technical skills | Did not answer basic questions | Not a fit"},
            {"submission_id": "S009", "interview_round": "Phone Screen",
             "interview_date": "2026-03-25", "avg_rating": 2.0,
             "feedback_line_count": 2, "sample_comments": "Communication gap | Could not explain past projects"},
        ],
    }


def data_fetch_node(state: OpsState) -> dict:
    """Fetch operational data from TG Database or fixtures."""
    log.info("[data_fetch] run_id=%s  fixture_mode=%s", state["run_id"], settings.tgap_fixture_only)

    try:
        if settings.tgap_fixture_only:
            raw = _build_fixture_data()
            log.info("[data_fetch] Fixture data loaded (%d datasets)", len(raw))
        else:
            raw: Dict[str, Any] = {}
            limit = settings.mysql_max_rows
            window = settings.data_window_days

            for name, sql in _QUERIES.items():
                try:
                    rows = tg_db.execute_query(sql.strip(), {"limit": limit, "window": window})
                    raw[name] = rows
                    log.info("[data_fetch] %s → %d rows (window=%d days)", name, len(rows), window)
                except Exception as exc:
                    log.warning("[data_fetch] Query '%s' failed: %s — continuing", name, exc)
                    raw[name] = []

            log.info(
                "[data_fetch] Complete: positions=%d subs=%d interviews=%d feedback=%d",
                len(raw.get("open_positions", [])),
                len(raw.get("submissions_aging", [])),
                len(raw.get("interview_breakdown", [])),
                len(raw.get("feedback_by_round", [])),
            )

        return {
            "raw_data": raw,
            "current_node": "data_fetch",
            "errors": [],
        }

    except Exception as exc:
        log.exception("[data_fetch] Fatal error: %s", exc)
        return {
            "raw_data": {},
            "current_node": "data_fetch",
            "errors": [f"data_fetch: {exc}"],
        }
