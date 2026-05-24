from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.admin.deps import CurrentAdminUser
from src.api.admin.render import admin_render
from src.core.acl import require_admin_permission
from src.database.base import get_db_session

from .service import (
    count_events,
    distinct_event_types,
    get_event,
    list_events,
    purge_old_events,
)

router = APIRouter(prefix="/admin/com_audit", tags=["com_audit"])

_PAGE_SIZE = 50


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).replace(tzinfo=UTC)
    except ValueError:
        return None


@router.get("", response_class=HTMLResponse)
async def index(
    request: Request,
    current_user: CurrentAdminUser,
    _acl: object = Depends(require_admin_permission("audit.view")),
    db: AsyncSession = Depends(get_db_session),
    event: str | None = None,
    actor_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
):
    page = max(1, page)
    offset = (page - 1) * _PAGE_SIZE

    df = _parse_date(date_from)
    dt = _parse_date(date_to)

    entries = await list_events(
        db, event=event or None, actor_id=actor_id,
        date_from=df, date_to=dt, limit=_PAGE_SIZE, offset=offset,
    )
    total = await count_events(db, event=event or None, actor_id=actor_id, date_from=df, date_to=dt)
    event_types = await distinct_event_types(db)
    pages = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)

    return await admin_render(
        "admin/com_audit/index.html", request, db,
        user=current_user,
        entries=entries,
        total=total,
        page=page,
        pages=pages,
        event_types=event_types,
        filter_event=event or "",
        filter_actor_id=actor_id or "",
        filter_date_from=date_from or "",
        filter_date_to=date_to or "",
    )


@router.get("/{entry_id}", response_class=HTMLResponse)
async def detail(
    request: Request,
    entry_id: int,
    current_user: CurrentAdminUser,
    _acl: object = Depends(require_admin_permission("audit.view")),
    db: AsyncSession = Depends(get_db_session),
):
    entry = await get_event(db, entry_id)
    if entry is None:
        return RedirectResponse("/admin/com_audit", status_code=303)

    return await admin_render(
        "admin/com_audit/detail.html", request, db,
        user=current_user,
        entry=entry,
    )


@router.post("/purge", response_class=HTMLResponse)
async def purge(
    request: Request,
    current_user: CurrentAdminUser,
    _acl: object = Depends(require_admin_permission("audit.purge")),
    db: AsyncSession = Depends(get_db_session),
):
    from sqlalchemy import select
    from src.database.models.component import InstalledComponent

    retention_days = 90
    comp = (
        await db.execute(
            select(InstalledComponent).where(InstalledComponent.name == "com_audit")
        )
    ).scalar_one_or_none()
    if comp and isinstance(comp.settings, dict):
        try:
            retention_days = int(comp.settings.get("retention_days", 90))
        except (TypeError, ValueError):
            pass

    deleted = await purge_old_events(db, retention_days=retention_days)

    request.session["flash"] = {
        "type": "success",
        "text": f"Smazáno {deleted} starých záznamů (retence {retention_days} dní).",
    }
    return RedirectResponse("/admin/com_audit", status_code=303)
