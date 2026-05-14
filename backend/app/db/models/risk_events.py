"""Risk event model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class RiskEvent(Base):
    __tablename__ = "risk_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    risk_category: Mapped[str] = mapped_column(String(80), nullable=False)
    risk_level: Mapped[str] = mapped_column(
        Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="risk_level"),
        nullable=False,
        default="MEDIUM",
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    affected_entity: Mapped[str] = mapped_column(String(256), nullable=True)
    account_name: Mapped[str] = mapped_column(String(128), nullable=True)
    recruiter_name: Mapped[str] = mapped_column(String(128), nullable=True)
    req_id: Mapped[str] = mapped_column(String(64), nullable=True)
    impact_score: Mapped[float] = mapped_column(Float, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_risk_events_category_level", "risk_category", "risk_level"),
        Index("ix_risk_events_account", "account_name"),
    )
