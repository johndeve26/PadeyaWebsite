"""Checkout question archive + subresource lifecycle support.

Revision ID: 20260717_0030
Revises: 20260717_0029
Create Date: 2026-07-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260717_0030"
down_revision = "20260717_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "event_checkout_questions",
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="active",
        ),
    )
    op.add_column(
        "event_checkout_questions",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_event_checkout_questions_status",
        "event_checkout_questions",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_event_checkout_questions_status",
        table_name="event_checkout_questions",
    )
    op.drop_column("event_checkout_questions", "archived_at")
    op.drop_column("event_checkout_questions", "status")
