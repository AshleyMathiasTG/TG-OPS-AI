"""Alerts API."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.db.models.alerts import Alert
from app.schemas.alerts import AlertMarkRead, AlertResponse
from app.core.logging_config import get_logger

router = APIRouter(prefix="/alerts", tags=["alerts"])
log = get_logger(__name__)


@router.get("")
async def list_alerts(
    severity: Optional[str] = Query(None),
    is_read: Optional[bool] = Query(None),
    limit: int = Query(200, le=500),
    db: AsyncSession = Depends(get_db),
) -> List[Dict]:
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.data_window_days)
        stmt = (
            select(Alert)
            .where(Alert.is_dismissed == False)
            .where(Alert.created_at >= cutoff)
            .order_by(Alert.created_at.desc())
            .limit(limit)
        )
        if severity:
            stmt = stmt.where(Alert.severity == severity.upper())
        if is_read is not None:
            stmt = stmt.where(Alert.is_read == is_read)
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "id": str(r.id), "run_id": r.run_id, "alert_type": r.alert_type,
                "severity": r.severity, "title": r.title, "summary": r.summary,
                "entity_name": r.entity_name, "is_read": r.is_read,
                "is_dismissed": r.is_dismissed, "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    except Exception as exc:
        log.warning("[alerts] DB query failed: %s", exc)
        return []


@router.patch("/mark-read")
async def mark_alerts_read(
    body: AlertMarkRead,
    db: AsyncSession = Depends(get_db),
) -> Dict:
    try:
        await db.execute(
            update(Alert).where(Alert.id.in_(body.ids)).values(is_read=True)
        )
        await db.commit()
    except Exception as exc:
        log.warning("[alerts] mark-read failed: %s", exc)
    return {"updated": len(body.ids)}


@router.delete("/{alert_id}")
async def dismiss_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Dict:
    try:
        await db.execute(
            update(Alert).where(Alert.id == alert_id).values(is_dismissed=True)
        )
        await db.commit()
    except Exception as exc:
        log.warning("[alerts] dismiss failed: %s", exc)
    return {"dismissed": str(alert_id)}
