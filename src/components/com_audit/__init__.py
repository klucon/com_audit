from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.registry import ComponentRegistry

_COMPONENT_DIR = Path(__file__).parent
_manifest: dict = {}


async def upgrade_schema(engine: object) -> None:
    from src.components.com_audit.schema import upgrade_schema as _up
    await _up(engine)


async def uninstall_schema(engine: object) -> None:
    from src.components.com_audit.schema import uninstall_schema as _down
    await _down(engine)


def _load_manifest() -> dict:
    global _manifest
    if not _manifest:
        try:
            _manifest = json.loads((_COMPONENT_DIR / "manifest.json").read_text(encoding="utf-8"))
        except Exception:
            _manifest = {}
    return _manifest


def setup(reg: ComponentRegistry) -> None:
    from src.core.hooks import hooks
    from src.i18n.translator import translator

    from src.components.com_audit import admin
    from src.components.com_audit.handlers import (
        on_app_shutdown,
        on_app_startup,
        on_user_created,
        on_user_deleted,
        on_user_login,
        on_user_logout,
        on_user_updated,
    )

    manifest = _load_manifest()

    reg.register("com_audit", "src.components.com_audit")
    reg.register_display_name(
        "com_audit",
        manifest.get("display_name_key", "extensions.name.com_audit"),
    )
    reg.register_admin_url("com_audit", manifest.get("admin_url", "/admin/com_audit"))
    reg.register_router(admin.router)

    translator.load_domain("com_audit", _COMPONENT_DIR / "i18n")

    hooks.on("user.login", on_user_login)
    hooks.on("user.logout", on_user_logout)
    hooks.on("user.created", on_user_created)
    hooks.on("user.updated", on_user_updated)
    hooks.on("user.deleted", on_user_deleted)
    hooks.on("app.startup", on_app_startup)
    hooks.on("app.shutdown", on_app_shutdown)
