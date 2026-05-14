"""Notifications API."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.db.models.notifications import Notification
from app.schemas.notifications import NotificationMarkRead
from app.core.logging_config import get_logger

router = APIRouter(prefix="/notifications", tags=["notifications"])
log = get_logger(__name__)


@router.get("")
async def list_notifications(
    priority: Optional[str] = Query(None),
    is_read: Optional[bool] = Query(None),
    limit: int = Query(200, le=500),
    db: AsyncSession = Depends(get_db),
) -> List[Dict]:
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.data_window_days)
        stmt = (
            select(Notification)
            .where(Notification.created_at >= cutoff)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        if priority:
            stmt = stmt.where(Notification.priority == priority.upper())
        if is_read is not None:
            stmt = stmt.where(Notification.is_read == is_read)
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "id": str(r.id), "run_id": r.run_id, "priority": r.priority,
                "channel": r.channel, "title": r.title, "body": r.body,
                "is_read": r.is_read, "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    except Exception as exc:
        log.warning("[notifications] DB query failed: %s", exc)
        return []


@router.get("/unread-count")
async def unread_count(db: AsyncSession = Depends(get_db)) -> Dict:
    try:
        from sqlalchemy import func
        count = await db.scalar(
            select(func.count(Notification.id)).where(Notification.is_read == False)
        )
        return {"unread": count or 0}
    except Exception:
        return {"unread": 0}


@router.patch("/mark-read")
async def mark_notifications_read(
    body: NotificationMarkRead,
    db: AsyncSession = Depends(get_db),
) -> Dict:
    try:
        await db.execute(
            update(Notification).where(Notification.id.in_(body.ids)).values(is_read=True)
        )
        await db.commit()
    except Exception as exc:
        log.warning("[notifications] mark-read failed: %s", exc)
    return {"updated": len(body.ids)}
