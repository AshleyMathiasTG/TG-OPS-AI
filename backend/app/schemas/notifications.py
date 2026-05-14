"""Notification schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: UUID
    run_id: Optional[str] = None
    priority: str
    channel: str
    title: str
    body: Optional[str] = None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationMarkRead(BaseModel):
    ids: list[UUID]
