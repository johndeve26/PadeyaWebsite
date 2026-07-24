"""Create admin notification system tables.

Revision ID: 20260720_0100
Revises: 20260720_0099
Create Date: 2026-07-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260720_0100"
down_revision = "20260720_0099"
branch_labels = None
depends_on = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "notification_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("type_key", sa.String(length=80), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("title_template", sa.String(length=200), nullable=False),
        sa.Column("body_template", sa.String(length=500), nullable=False),
        sa.Column("cta_text", sa.String(length=80), nullable=True),
        sa.Column("cta_url_template", sa.String(length=300), nullable=True),
        sa.Column("email_template_key", sa.String(length=80), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
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
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notification_templates_type_key", "notification_templates", ["type_key"]
    )

    op.create_table(
        "notification_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("type_key", sa.String(length=80), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "channel_in_app", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "channel_push", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "channel_email", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "audience",
            sa.String(length=64),
            nullable=False,
            server_default="context_recipients",
        ),
        sa.Column("template_id", sa.Uuid(), nullable=True),
        sa.Column(
            "cooldown_seconds", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "send_mode", sa.String(length=16), nullable=False, server_default="immediate"
        ),
        sa.Column(
            "classification",
            sa.String(length=32),
            nullable=False,
            server_default="transactional",
        ),
        sa.Column(
            "respect_user_prefs",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("audience_filters", JSON_TYPE, nullable=False, server_default="{}"),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
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
            ["template_id"], ["notification_templates.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("type_key", name="uq_notification_settings_type_key"),
    )
    op.create_index(
        "ix_notification_settings_type_key", "notification_settings", ["type_key"]
    )

    op.create_table(
        "notification_campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.String(length=500), nullable=False),
        sa.Column("cta_text", sa.String(length=80), nullable=True),
        sa.Column("cta_url", sa.String(length=300), nullable=True),
        sa.Column(
            "channel_in_app", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "channel_push", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "channel_email", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "audience_mode",
            sa.String(length=64),
            nullable=False,
            server_default="selected_users",
        ),
        sa.Column("audience_filters", JSON_TYPE, nullable=False, server_default="{}"),
        sa.Column(
            "status", sa.String(length=24), nullable=False, server_default="draft"
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "recipient_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=False),
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
            ["created_by_admin_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notification_campaigns_status", "notification_campaigns", ["status"]
    )
    op.create_index(
        "ix_notification_campaigns_created_by_admin_id",
        "notification_campaigns",
        ["created_by_admin_id"],
    )

    op.create_table(
        "notification_campaign_recipients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status", sa.String(length=24), nullable=False, server_default="pending"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["notification_campaigns.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id",
            "user_id",
            name="uq_notification_campaign_recipients_campaign_user",
        ),
    )
    op.create_index(
        "ix_notification_campaign_recipients_campaign_id",
        "notification_campaign_recipients",
        ["campaign_id"],
    )
    op.create_index(
        "ix_notification_campaign_recipients_user_id",
        "notification_campaign_recipients",
        ["user_id"],
    )

    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("type_key", sa.String(length=80), nullable=False),
        sa.Column("recipient_user_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column(
            "status", sa.String(length=24), nullable=False, server_default="pending"
        ),
        sa.Column("dedupe_key", sa.String(length=200), nullable=True),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("in_app_notification_id", sa.Uuid(), nullable=True),
        sa.Column("error_reason", sa.String(length=240), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["notification_campaigns.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_admin_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notification_deliveries_type_key", "notification_deliveries", ["type_key"]
    )
    op.create_index(
        "ix_notification_deliveries_recipient_user_id",
        "notification_deliveries",
        ["recipient_user_id"],
    )
    op.create_index(
        "ix_notification_deliveries_status", "notification_deliveries", ["status"]
    )
    op.create_index(
        "ix_notification_deliveries_dedupe_key",
        "notification_deliveries",
        ["dedupe_key"],
    )
    op.create_index(
        "ix_notification_deliveries_campaign_id",
        "notification_deliveries",
        ["campaign_id"],
    )

    op.create_table(
        "notification_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=80), nullable=True),
        sa.Column("details", JSON_TYPE, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notification_audit_logs_action", "notification_audit_logs", ["action"]
    )
    op.create_index(
        "ix_notification_audit_logs_created_at",
        "notification_audit_logs",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_table("notification_audit_logs")
    op.drop_table("notification_deliveries")
    op.drop_table("notification_campaign_recipients")
    op.drop_table("notification_campaigns")
    op.drop_table("notification_settings")
    op.drop_table("notification_templates")
