from __future__ import annotations

from typing import Any


def _ip(request: Any) -> str:
    if request is None:
        return ""
    client = getattr(request, "client", None)
    if client:
        return str(client.host)
    return ""


async def _write(event: str, actor_id: int | None, actor_name: str, ip: str, ctx: dict) -> None:
    from src.database.base import async_session_factory
    from .service import log_event

    if async_session_factory is None:
        return
    async with async_session_factory() as db:
        await log_event(db, event=event, actor_id=actor_id, actor_name=actor_name,
                        ip_address=ip, context=ctx)


async def on_user_login(*, user_id: int | None = None, username: str = "",
                        request: Any = None, **kwargs: Any) -> None:
    await _write("user.login", user_id, username, _ip(request), {})


async def on_user_logout(*, user_id: int | None = None, username: str = "",
                         request: Any = None, **kwargs: Any) -> None:
    await _write("user.logout", user_id, username, _ip(request), {})


async def on_user_created(*, user_id: int | None = None, username: str = "",
                          **kwargs: Any) -> None:
    await _write("user.created", user_id, username, "", {})


async def on_user_updated(*, user_id: int | None = None, username: str = "",
                          **kwargs: Any) -> None:
    await _write("user.updated", user_id, username, "", {})


async def on_user_deleted(*, user_id: int | None = None, username: str = "",
                          **kwargs: Any) -> None:
    await _write("user.deleted", user_id, username, "", {})


async def on_app_startup(**kwargs: Any) -> None:
    await _write("app.startup", None, "system", "", {})


async def on_app_shutdown(**kwargs: Any) -> None:
    await _write("app.shutdown", None, "system", "", {})
