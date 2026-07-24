"""Add push provider mode (web_push | log) to push_provider_settings.

Revision ID: 20260719_0064
Revises: 20260719_0063
Create Date: 2026-07-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260719_0064"
down_revision = "20260719_0063"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "push_provider_settings",
        sa.Column(
            "provider",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'log'"),
        ),
    )
    op.create_index(
        "ix_push_delivery_events_status",
        "push_delivery_events",
        ["status"],
    )
    op.create_index(
        "ix_push_delivery_events_created_at",
        "push_delivery_events",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_push_delivery_events_created_at", table_name="push_delivery_events")
    op.drop_index("ix_push_delivery_events_status", table_name="push_delivery_events")
    op.drop_column("push_provider_settings", "provider")
