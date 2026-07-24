"""DB overrides for optional runtime settings (never boot-critical Class A)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.core.database import Base


class RuntimeSetting(Base):
    """One row per allowlisted override key.

    Non-secrets → ``value_plain``. Secrets → ``value_encrypted`` + ``first_four`` / ``last_four`` only.
    Prefer reset (delete row) over hard-delete of audit history.
    """

    __tablename__ = "runtime_settings"
    __table_args__ = (UniqueConstraint("key", name="uq_runtime_settings_key"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    value_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_plain: Mapped[Any | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    value_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="string"
    )
    is_secret: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_editable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_required_for_runtime: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    # Last-write label; API also recomputes db|env|default for display.
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="db")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_schema_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    last_four: Mapped[str | None] = mapped_column(String(8), nullable=True)
    first_four: Mapped[str | None] = mapped_column(String(8), nullable=True)
    updated_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
