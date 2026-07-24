"""Transactional email outbox + user email preferences.

Revision ID: 20260719_0060
Revises: 20260718_0059
Create Date: 2026-07-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260719_0060"
down_revision = "20260718_0059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_events",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("template", sa.String(80), nullable=False),
        sa.Column("recipient_email", sa.String(320), nullable=False),
        sa.Column("recipient_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("provider", sa.String(32), nullable=True),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column(
            "context_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dedupe_key", sa.String(200), nullable=True),
        sa.Column("preference_key", sa.String(64), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("body_html", sa.Text(), nullable=True),
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
            ["recipient_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("dedupe_key", name="uq_email_events_dedupe_key"),
    )
    op.create_index("ix_email_events_template", "email_events", ["template"])
    op.create_index(
        "ix_email_events_recipient_email", "email_events", ["recipient_email"]
    )
    op.create_index(
        "ix_email_events_recipient_user_id", "email_events", ["recipient_user_id"]
    )
    op.create_index("ix_email_events_status", "email_events", ["status"])

    op.create_table(
        "user_email_preferences",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "email_ticket_updates",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "email_merch_updates",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "email_event_reminders",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "email_messages",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "email_fan_connect",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "email_sponsor_updates",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "email_host_activity",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "email_marketing",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "email_security",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("unsubscribed_marketing_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_user_email_preferences_user_id"),
    )
    op.create_index(
        "ix_user_email_preferences_user_id", "user_email_preferences", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_user_email_preferences_user_id", table_name="user_email_preferences")
    op.drop_table("user_email_preferences")
    op.drop_index("ix_email_events_status", table_name="email_events")
    op.drop_index("ix_email_events_recipient_user_id", table_name="email_events")
    op.drop_index("ix_email_events_recipient_email", table_name="email_events")
    op.drop_index("ix_email_events_template", table_name="email_events")
    op.drop_table("email_events")
