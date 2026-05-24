from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from src.database.base import Base


def _now() -> datetime:
    return datetime.now(UTC)


class AuditLog(Base):
    __tablename__ = "com_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actor_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    actor_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), default="", nullable=False)
    context: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False, index=True
    )
