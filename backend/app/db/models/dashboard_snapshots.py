"""Periodic dashboard snapshot for KPI trend tracking."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class DashboardSnapshot(Base):
    __tablename__ = "dashboard_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=True)
    open_risks: Mapped[int] = mapped_column(Integer, default=0)
    sla_breaches: Mapped[int] = mapped_column(Integer, default=0)
    active_alerts: Mapped[int] = mapped_column(Integer, default=0)
    pending_approvals: Mapped[int] = mapped_column(Integer, default=0)
    critical_issues: Mapped[int] = mapped_column(Integer, default=0)
    kpi_json: Mapped[str] = mapped_column(Text, nullable=True)   # full KPI blob
    trend_json: Mapped[str] = mapped_column(Text, nullable=True)  # trend series
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
