"""User feedback (thumbs up/down) on approvals and recommendations."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    approval_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("approvals.id"), nullable=False, index=True
    )
    sentiment: Mapped[str] = mapped_column(
        Enum("THUMBS_UP", "THUMBS_DOWN", name="feedback_sentiment"),
        nullable=False,
    )
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    submitted_by: Mapped[str] = mapped_column(String(128), nullable=True, default="anonymous")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    approval: Mapped["Approval"] = relationship("Approval", back_populates="feedback")  # type: ignore[name-defined]
