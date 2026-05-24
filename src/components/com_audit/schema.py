from __future__ import annotations

from sqlalchemy import inspect, text

from .models import AuditLog

_TABLES_CREATE_ORDER = [AuditLog.__table__]
_TABLES_DROP_ORDER = [AuditLog.__table__]


async def upgrade_schema(engine: object) -> None:
    from sqlalchemy.ext.asyncio import AsyncEngine

    assert isinstance(engine, AsyncEngine)
    async with engine.begin() as conn:
        existing = await conn.run_sync(lambda c: inspect(c).get_table_names())
        for table in _TABLES_CREATE_ORDER:
            if table.name not in existing:
                await conn.run_sync(table.create)


async def uninstall_schema(engine: object) -> None:
    from sqlalchemy.ext.asyncio import AsyncEngine

    assert isinstance(engine, AsyncEngine)
    async with engine.begin() as conn:
        existing = await conn.run_sync(lambda c: inspect(c).get_table_names())
        for table in _TABLES_DROP_ORDER:
            if table.name in existing:
                await conn.execute(text(f"DROP TABLE {table.name}"))
