from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.components.com_audit.service import (
    count_events,
    distinct_event_types,
    get_event,
    list_events,
    log_event,
    purge_old_events,
)
from src.database.models import User


# ── log_event ─────────────────────────────────────────────────────────────────

async def test_log_event_basic(db_session: AsyncSession) -> None:
    entry = await log_event(db_session, event="user.login", actor_id=1, actor_name="alice",
                            ip_address="127.0.0.1")
    assert entry.id is not None
    assert entry.event == "user.login"
    assert entry.actor_name == "alice"
    assert entry.ip_address == "127.0.0.1"


async def test_log_event_sanitizes_sensitive_keys(db_session: AsyncSession) -> None:
    entry = await log_event(
        db_session, event="user.created",
        context={"username": "bob", "password": "secret123", "token": "abc"}
    )
    assert "secret123" not in entry.context
    assert "abc" not in entry.context
    assert "bob" in entry.context


async def test_log_event_empty_context(db_session: AsyncSession) -> None:
    entry = await log_event(db_session, event="app.startup")
    assert entry.context == "{}"


# ── list_events / count_events ────────────────────────────────────────────────

async def test_list_events_filter_by_event(db_session: AsyncSession) -> None:
    await log_event(db_session, event="user.login", actor_id=1, actor_name="alice")
    await log_event(db_session, event="user.logout", actor_id=1, actor_name="alice")
    await log_event(db_session, event="user.login", actor_id=2, actor_name="bob")

    logins = await list_events(db_session, event="user.login")
    assert len(logins) == 2
    assert all(e.event == "user.login" for e in logins)


async def test_list_events_filter_by_actor(db_session: AsyncSession) -> None:
    await log_event(db_session, event="user.login", actor_id=1, actor_name="alice")
    await log_event(db_session, event="user.login", actor_id=2, actor_name="bob")

    entries = await list_events(db_session, actor_id=1)
    assert len(entries) == 1
    assert entries[0].actor_name == "alice"


async def test_list_events_filter_by_date(db_session: AsyncSession) -> None:
    old = AuditLogFactory(event="user.login", days_ago=10)
    recent = AuditLogFactory(event="user.login", days_ago=1)
    db_session.add(old)
    db_session.add(recent)
    await db_session.commit()

    cutoff = datetime.now(UTC) - timedelta(days=5)
    entries = await list_events(db_session, date_from=cutoff)
    assert all(e.created_at >= cutoff for e in entries)


async def test_count_events(db_session: AsyncSession) -> None:
    await log_event(db_session, event="user.login")
    await log_event(db_session, event="user.login")
    await log_event(db_session, event="user.logout")

    assert await count_events(db_session, event="user.login") == 2
    assert await count_events(db_session) == 3


# ── get_event ─────────────────────────────────────────────────────────────────

async def test_get_event_found(db_session: AsyncSession) -> None:
    entry = await log_event(db_session, event="user.created", actor_name="carol")
    fetched = await get_event(db_session, entry.id)
    assert fetched is not None
    assert fetched.id == entry.id


async def test_get_event_not_found(db_session: AsyncSession) -> None:
    result = await get_event(db_session, 99999)
    assert result is None


# ── purge_old_events ──────────────────────────────────────────────────────────

async def test_purge_old_events(db_session: AsyncSession) -> None:
    old = AuditLogFactory(event="user.login", days_ago=100)
    fresh = AuditLogFactory(event="user.login", days_ago=1)
    db_session.add(old)
    db_session.add(fresh)
    await db_session.commit()

    deleted = await purge_old_events(db_session, retention_days=30)
    assert deleted == 1

    remaining = await list_events(db_session)
    assert len(remaining) == 1
    assert remaining[0].created_at > datetime.now(UTC) - timedelta(days=30)


# ── distinct_event_types ──────────────────────────────────────────────────────

async def test_distinct_event_types(db_session: AsyncSession) -> None:
    await log_event(db_session, event="user.login")
    await log_event(db_session, event="user.login")
    await log_event(db_session, event="user.logout")
    await log_event(db_session, event="app.startup")

    types = await distinct_event_types(db_session)
    assert sorted(types) == ["app.startup", "user.login", "user.logout"]


# ── admin routes ──────────────────────────────────────────────────────────────

async def test_admin_index_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/admin/com_audit", follow_redirects=False)
    assert resp.status_code in (302, 303)


async def test_admin_index_ok(auth_client: AsyncClient, db_session: AsyncSession) -> None:
    await log_event(db_session, event="user.login", actor_name="alice")
    resp = await auth_client.get("/admin/com_audit")
    assert resp.status_code == 200
    assert "user.login" in resp.text


async def test_admin_detail_ok(auth_client: AsyncClient, db_session: AsyncSession) -> None:
    entry = await log_event(db_session, event="user.created", actor_name="dave",
                            ip_address="10.0.0.1")
    resp = await auth_client.get(f"/admin/com_audit/{entry.id}")
    assert resp.status_code == 200
    assert "dave" in resp.text
    assert "10.0.0.1" in resp.text


async def test_admin_detail_missing(auth_client: AsyncClient) -> None:
    resp = await auth_client.get("/admin/com_audit/99999", follow_redirects=False)
    assert resp.status_code == 303


async def test_admin_index_filter_event(auth_client: AsyncClient, db_session: AsyncSession) -> None:
    await log_event(db_session, event="user.login", actor_name="alice")
    await log_event(db_session, event="user.logout", actor_name="alice")

    resp = await auth_client.get("/admin/com_audit?event=user.login")
    assert resp.status_code == 200
    assert "user.login" in resp.text


# ── helpers ───────────────────────────────────────────────────────────────────

def AuditLogFactory(*, event: str, days_ago: int) -> "AuditLog":
    from src.components.com_audit.models import AuditLog
    return AuditLog(
        event=event,
        actor_id=None,
        actor_name="",
        ip_address="",
        context="{}",
        created_at=datetime.now(UTC) - timedelta(days=days_ago),
    )
