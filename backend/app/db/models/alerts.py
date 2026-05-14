"""Alert model — operational alerts detected by AI agents."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(
        Enum("INFO", "WARNING", "CRITICAL", name="alert_severity"),
        nullable=False,
        default="WARNING",
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=True)  # recruiter/account/req
    entity_id: Mapped[str] = mapped_column(String(128), nullable=True)
    entity_name: Mapped[str] = mapped_column(String(256), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=True)  # JSON blob
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_alerts_severity_created", "severity", "created_at"),
        Index("ix_alerts_type", "alert_type"),
    )
