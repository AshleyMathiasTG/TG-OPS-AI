"""SLA breach/risk event model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class SlaEvent(Base):
    __tablename__ = "sla_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sla_type: Mapped[str] = mapped_column(String(80), nullable=False)
    breach_status: Mapped[str] = mapped_column(
        Enum("AT_RISK", "BREACHED", "RESOLVED", name="sla_breach_status"),
        nullable=False,
        default="AT_RISK",
    )
    req_id: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    req_title: Mapped[str] = mapped_column(String(256), nullable=True)
    account_name: Mapped[str] = mapped_column(String(128), nullable=True)
    recruiter_name: Mapped[str] = mapped_column(String(128), nullable=True)
    candidate_name: Mapped[str] = mapped_column(String(128), nullable=True)
    aging_days: Mapped[int] = mapped_column(Integer, nullable=True)
    sla_threshold_days: Mapped[int] = mapped_column(Integer, nullable=True)
    current_status: Mapped[str] = mapped_column(String(128), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
