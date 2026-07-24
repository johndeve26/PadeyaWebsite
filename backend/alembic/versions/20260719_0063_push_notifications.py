"""Push subscriptions, VAPID settings, push prefs, in-app lifecycle columns.

Revision ID: 20260719_0063
Revises: 20260719_0062
Create Date: 2026-07-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260719_0063"
down_revision = "20260719_0062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "in_app_notifications",
        sa.Column("dedupe_key", sa.String(200), nullable=True),
    )
    op.add_column(
        "in_app_notifications",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "in_app_notifications",
        sa.Column("popup_shown_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_in_app_notifications_dedupe_key",
        "in_app_notifications",
        ["dedupe_key"],
    )

    for col in (
        "push_ticket_updates",
        "push_merch_updates",
        "push_event_reminders",
        "push_messages",
        "push_fan_connect",
        "push_sponsor_updates",
        "push_host_activity",
        "push_marketing",
    ):
        default = "false"
        if col in {
            "push_ticket_updates",
            "push_merch_updates",
            "push_event_reminders",
            "push_sponsor_updates",
            "push_host_activity",
        }:
            default = "true"
        op.add_column(
            "user_email_preferences",
            sa.Column(
                col,
                sa.Boolean(),
                nullable=False,
                server_default=sa.text(default),
            ),
        )
    op.add_column(
        "user_email_preferences",
        sa.Column(
            "push_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.create_table(
        "push_provider_settings",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "push_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("vapid_public_key", sa.Text(), nullable=True),
        sa.Column("vapid_private_key_encrypted", sa.Text(), nullable=True),
        sa.Column("vapid_subject", sa.String(320), nullable=True),
        sa.Column("vapid_private_last4", sa.String(8), nullable=True),
        sa.Column("last_test_status", sa.String(32), nullable=True),
        sa.Column("last_test_error", sa.Text(), nullable=True),
        sa.Column("last_test_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(as_uuid=True), nullable=True),
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
            ["created_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_push_provider_settings_is_active",
        "push_provider_settings",
        ["is_active"],
    )

    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh_encrypted", sa.Text(), nullable=False),
        sa.Column("auth_encrypted", sa.Text(), nullable=False),
        sa.Column("user_agent", sa.String(400), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint("endpoint", name="uq_push_subscriptions_endpoint"),
    )
    op.create_index("ix_push_subscriptions_user_id", "push_subscriptions", ["user_id"])

    op.create_table(
        "push_delivery_events",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("subscription_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("notification_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["subscription_id"], ["push_subscriptions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["notification_id"], ["in_app_notifications.id"], ondelete="SET NULL"
        ),
    )


def downgrade() -> None:
    op.drop_table("push_delivery_events")
    op.drop_index("ix_push_subscriptions_user_id", table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
    op.drop_index("ix_push_provider_settings_is_active", table_name="push_provider_settings")
    op.drop_table("push_provider_settings")
    for col in (
        "push_enabled",
        "push_ticket_updates",
        "push_merch_updates",
        "push_event_reminders",
        "push_messages",
        "push_fan_connect",
        "push_sponsor_updates",
        "push_host_activity",
        "push_marketing",
    ):
        op.drop_column("user_email_preferences", col)
    op.drop_index("ix_in_app_notifications_dedupe_key", table_name="in_app_notifications")
    op.drop_column("in_app_notifications", "popup_shown_at")
    op.drop_column("in_app_notifications", "archived_at")
    op.drop_column("in_app_notifications", "dedupe_key")
