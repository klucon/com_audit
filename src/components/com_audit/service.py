from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AuditLog

_SENSITIVE_KEYS = frozenset(
    {"password", "hashed_password", "token", "secret", "key", "access_token", "refresh_token"}
)


def _sanitize(data: dict) -> str:
    clean = {k: ("***" if k in _SENSITIVE_KEYS else v) for k, v in data.items()}
    return json.dumps(clean, default=str, ensure_ascii=False)


async def log_event(
    db: AsyncSession,
    *,
    event: str,
    actor_id: int | None = None,
    actor_name: str = "",
    ip_address: str = "",
    context: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        event=event,
        actor_id=actor_id,
        actor_name=actor_name,
        ip_address=ip_address,
        context=_sanitize(context or {}),
        created_at=datetime.now(UTC),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def list_events(
    db: AsyncSession,
    *,
    event: str | None = None,
    actor_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AuditLog]:
    q = select(AuditLog).order_by(AuditLog.created_at.desc())
    if event:
        q = q.where(AuditLog.event == event)
    if actor_id is not None:
        q = q.where(AuditLog.actor_id == actor_id)
    if date_from:
        q = q.where(AuditLog.created_at >= date_from)
    if date_to:
        q = q.where(AuditLog.created_at <= date_to)
    q = q.limit(limit).offset(offset)
    return list((await db.execute(q)).scalars().all())


async def count_events(
    db: AsyncSession,
    *,
    event: str | None = None,
    actor_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> int:
    q = select(func.count()).select_from(AuditLog)
    if event:
        q = q.where(AuditLog.event == event)
    if actor_id is not None:
        q = q.where(AuditLog.actor_id == actor_id)
    if date_from:
        q = q.where(AuditLog.created_at >= date_from)
    if date_to:
        q = q.where(AuditLog.created_at <= date_to)
    return (await db.execute(q)).scalar_one()


async def get_event(db: AsyncSession, event_id: int) -> AuditLog | None:
    return (
        await db.execute(select(AuditLog).where(AuditLog.id == event_id))
    ).scalar_one_or_none()


async def purge_old_events(db: AsyncSession, *, retention_days: int) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    result = await db.execute(delete(AuditLog).where(AuditLog.created_at < cutoff))
    await db.commit()
    return result.rowcount


async def distinct_event_types(db: AsyncSession) -> list[str]:
    rows = (await db.execute(select(AuditLog.event).distinct().order_by(AuditLog.event))).scalars()
    return list(rows)
