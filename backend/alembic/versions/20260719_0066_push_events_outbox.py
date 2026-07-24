"""Add push_events outbox table (email-style drain).

Revision ID: 20260719_0066
Revises: 20260719_0065
Create Date: 2026-07-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260719_0066"
down_revision = "20260719_0065"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "push_events",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("recipient_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("template", sa.String(64), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("body", sa.String(240), nullable=False),
        sa.Column("action_url", sa.String(300), nullable=True),
        sa.Column("icon_url", sa.String(500), nullable=True),
        sa.Column("badge_url", sa.String(500), nullable=True),
        sa.Column(
            "data_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "attempts", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dedupe_key", sa.String(200), nullable=True),
        sa.Column("notification_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["notification_id"],
            ["in_app_notifications.id"],
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("dedupe_key", name="uq_push_events_dedupe_key"),
    )
    op.create_index("ix_push_events_status", "push_events", ["status"])
    op.create_index(
        "ix_push_events_recipient_user_id", "push_events", ["recipient_user_id"]
    )
    op.create_index("ix_push_events_created_at", "push_events", ["created_at"])
    op.create_index("ix_push_events_template", "push_events", ["template"])


def downgrade() -> None:
    op.drop_index("ix_push_events_template", table_name="push_events")
    op.drop_index("ix_push_events_created_at", table_name="push_events")
    op.drop_index("ix_push_events_recipient_user_id", table_name="push_events")
    op.drop_index("ix_push_events_status", table_name="push_events")
    op.drop_table("push_events")
