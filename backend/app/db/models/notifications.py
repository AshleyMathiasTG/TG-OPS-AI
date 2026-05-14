"""In-app notification model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    priority: Mapped[str] = mapped_column(
        Enum("INFO", "WARNING", "CRITICAL", name="notification_priority"),
        nullable=False,
        default="INFO",
    )
    channel: Mapped[str] = mapped_column(
        Enum("IN_APP", "EMAIL", "TEAMS", name="notification_channel"),
        nullable=False,
        default="IN_APP",
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    delivered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
