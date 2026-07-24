"""Create user_restrictions table; migrate legacy account_restrictions JSON.

Revision ID: 20260720_0096
Revises: 20260720_0095
Create Date: 2026-07-20
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "20260720_0096"
down_revision = "20260720_0095"
branch_labels = None
depends_on = None

_LEGACY_ALIASES = {
    "cannot_promote_as_ambassador": "cannot_join_ambassador_campaigns",
}


def upgrade() -> None:
    op.create_table(
        "user_restrictions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("restriction_key", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("internal_note", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=False),
        sa.Column("revoked_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["revoked_by_admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_user_restrictions_user_id", "user_restrictions", ["user_id"], unique=False
    )
    op.create_index(
        "ix_user_restrictions_restriction_key",
        "user_restrictions",
        ["restriction_key"],
        unique=False,
    )
    op.create_index(
        "ix_user_restrictions_status", "user_restrictions", ["status"], unique=False
    )
    op.create_index(
        "ix_user_restrictions_user_key_status",
        "user_restrictions",
        ["user_id", "restriction_key", "status"],
        unique=False,
    )

    conn = op.get_bind()
    users = conn.execute(
        sa.text(
            "SELECT id, account_restrictions, ambassadors_blocked FROM users "
            "WHERE account_restrictions IS NOT NULL OR ambassadors_blocked = true"
        )
    ).fetchall()

    now = datetime.now(timezone.utc)
    for row in users:
        user_id = row[0]
        raw = row[1]
        ambassadors_blocked = bool(row[2])
        keys: list[str] = []
        seen: set[str] = set()

        parsed: list = []
        if isinstance(raw, list):
            parsed = raw
        elif isinstance(raw, str) and raw.strip():
            try:
                loaded = json.loads(raw)
                if isinstance(loaded, list):
                    parsed = loaded
            except json.JSONDecodeError:
                parsed = []

        for item in parsed:
            if not isinstance(item, str):
                continue
            code = item.strip().lower().replace(" ", "_")
            code = _LEGACY_ALIASES.get(code, code)
            if code and code not in seen:
                seen.add(code)
                keys.append(code)

        if ambassadors_blocked and "cannot_join_ambassador_campaigns" not in seen:
            keys.append("cannot_join_ambassador_campaigns")
            seen.add("cannot_join_ambassador_campaigns")

        for key in keys:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO user_restrictions (
                        id, user_id, restriction_key, status, reason,
                        internal_note, starts_at, ends_at,
                        created_by_admin_id, revoked_by_admin_id, revoked_at,
                        created_at, updated_at
                    ) VALUES (
                        :id, :user_id, :restriction_key, 'active',
                        :reason, NULL, :now, NULL,
                        :user_id, NULL, NULL, :now, :now
                    )
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "user_id": str(user_id),
                    "restriction_key": key,
                    "reason": "Migrated from legacy account_restrictions",
                    "now": now,
                },
            )


def downgrade() -> None:
    op.drop_index("ix_user_restrictions_user_key_status", table_name="user_restrictions")
    op.drop_index("ix_user_restrictions_status", table_name="user_restrictions")
    op.drop_index("ix_user_restrictions_restriction_key", table_name="user_restrictions")
    op.drop_index("ix_user_restrictions_user_id", table_name="user_restrictions")
    op.drop_table("user_restrictions")
