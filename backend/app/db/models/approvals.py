"""Approval workflow model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recommendations.id"), nullable=False, index=True
    )
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    issue_summary: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    impact_level: Mapped[str] = mapped_column(String(32), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("PENDING", "APPROVED", "REJECTED", name="approval_status"),
        nullable=False,
        default="PENDING",
    )
    reviewer_note: Mapped[str] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_result: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    recommendation: Mapped["Recommendation"] = relationship(  # type: ignore[name-defined]
        "Recommendation", back_populates="approvals"
    )
    feedback: Mapped[list["Feedback"]] = relationship(  # type: ignore[name-defined]
        "Feedback", back_populates="approval", cascade="all, delete-orphan"
    )
