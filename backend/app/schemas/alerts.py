"""Alert schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class AlertResponse(BaseModel):
    id: UUID
    run_id: str
    alert_type: str
    severity: str
    title: str
    summary: Optional[str] = None
    entity_name: Optional[str] = None
    is_read: bool
    is_dismissed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertMarkRead(BaseModel):
    ids: list[UUID]


class AlertDismiss(BaseModel):
    ids: list[UUID]
