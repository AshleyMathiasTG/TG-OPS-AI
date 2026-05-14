"""AI-generated action recommendation model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    issue_key: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    issue_summary: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation_text: Mapped[str] = mapped_column(Text, nullable=False)
    escalation_path: Mapped[str] = mapped_column(Text, nullable=True)
    mitigation_steps: Mapped[str] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=True)
    impact_level: Mapped[str] = mapped_column(String(32), nullable=True)
    model_used: Mapped[str] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    approvals: Mapped[list["Approval"]] = relationship(  # type: ignore[name-defined]
        "Approval", back_populates="recommendation", cascade="all, delete-orphan"
    )
