"""ORM models — import all so Alembic discovers them."""
from app.db.models.alerts import Alert
from app.db.models.risk_events import RiskEvent
from app.db.models.sla_events import SlaEvent
from app.db.models.recommendations import Recommendation
from app.db.models.approvals import Approval
from app.db.models.feedback import Feedback
from app.db.models.notifications import Notification
from app.db.models.execution_logs import ExecutionLog
from app.db.models.issue_occurrences import IssueOccurrence
from app.db.models.dashboard_snapshots import DashboardSnapshot

__all__ = [
    "Alert",
    "RiskEvent",
    "SlaEvent",
    "Recommendation",
    "Approval",
    "Feedback",
    "Notification",
    "ExecutionLog",
    "IssueOccurrence",
    "DashboardSnapshot",
]
