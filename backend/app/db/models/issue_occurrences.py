"""Issue occurrence tracker for the consecutive-detection logic."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class IssueOccurrence(Base):
    __tablename__ = "issue_occurrences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    issue_key: Mapped[str] = mapped_column(String(256), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_name: Mapped[str] = mapped_column(String(256), nullable=True)
    account_name: Mapped[str] = mapped_column(String(128), nullable=True)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_detected_run: Mapped[str] = mapped_column(String(64), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    metadata_json: Mapped[str] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_issue_occurrences_key", "issue_key"),
        Index("ix_issue_occurrences_type", "issue_type", "occurrence_count"),
    )
