"""Enrich push_subscriptions with device metadata and failure lifecycle.

Revision ID: 20260719_0065
Revises: 20260719_0064
Create Date: 2026-07-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260719_0065"
down_revision = "20260719_0064"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "push_subscriptions",
        sa.Column("device_label", sa.String(120), nullable=True),
    )
    op.add_column(
        "push_subscriptions",
        sa.Column("platform", sa.String(64), nullable=True),
    )
    op.add_column(
        "push_subscriptions",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "push_subscriptions",
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "push_subscriptions",
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "push_subscriptions",
        sa.Column(
            "failure_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    # Existing non-revoked rows stay active; revoked rows become inactive.
    op.execute(
        """
        UPDATE push_subscriptions
        SET is_active = false
        WHERE revoked_at IS NOT NULL
        """
    )
    op.create_index(
        "ix_push_subscriptions_is_active",
        "push_subscriptions",
        ["is_active"],
    )
    op.create_index(
        "ix_push_subscriptions_user_active",
        "push_subscriptions",
        ["user_id", "is_active"],
    )


def downgrade() -> None:
    op.drop_index("ix_push_subscriptions_user_active", table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_is_active", table_name="push_subscriptions")
    op.drop_column("push_subscriptions", "failure_count")
    op.drop_column("push_subscriptions", "last_failure_at")
    op.drop_column("push_subscriptions", "last_success_at")
    op.drop_column("push_subscriptions", "is_active")
    op.drop_column("push_subscriptions", "platform")
    op.drop_column("push_subscriptions", "device_label")
