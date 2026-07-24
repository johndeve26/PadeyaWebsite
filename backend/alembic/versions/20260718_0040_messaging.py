"""In-app messaging (fan ↔ host).

Revision ID: 20260718_0040
Revises: 20260718_0039
Create Date: 2026-07-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
revision = "20260718_0040"
down_revision = "20260718_0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "message_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "allow_messages_from_hosts_i_follow",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "allow_messages_from_hosts_i_attended",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "allow_messages_from_public",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "message_requests_enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "allow_messages_from_followers",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "allow_messages_from_ticket_buyers",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "allow_messages_from_public_host",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "allow_event_inquiries",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "auto_reply_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("auto_reply_message", sa.String(length=500), nullable=True),
        sa.Column("messaging_suspended_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_message_settings_user_id"),
    )
    op.create_index("ix_message_settings_user_id", "message_settings", ["user_id"])

    op.create_table(
        "message_threads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("thread_type", sa.String(length=32), nullable=False),
        sa.Column("fan_user_id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("host_user_id", sa.Uuid(), nullable=False),
        sa.Column("related_event_id", sa.Uuid(), nullable=True),
        sa.Column("related_order_id", sa.Uuid(), nullable=True),
        sa.Column("related_ticket_id", sa.Uuid(), nullable=True),
        sa.Column("related_inquiry_id", sa.Uuid(), nullable=True),
        sa.Column("subject", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("initiated_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("last_message_id", sa.Uuid(), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_message_preview", sa.String(length=240), nullable=True),
        sa.Column("fan_last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("host_last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fan_archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("host_archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["fan_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["initiated_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["related_event_id"], ["events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["related_order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["related_ticket_id"], ["tickets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fan_user_id", "host_id", name="uq_message_threads_fan_host"),
    )
    op.create_index("ix_message_threads_fan_user_id", "message_threads", ["fan_user_id"])
    op.create_index("ix_message_threads_host_id", "message_threads", ["host_id"])
    op.create_index("ix_message_threads_host_user_id", "message_threads", ["host_user_id"])
    op.create_index("ix_message_threads_status", "message_threads", ["status"])
    op.create_index("ix_message_threads_last_message_at", "message_threads", ["last_message_at"])

    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("thread_id", sa.Uuid(), nullable=False),
        sa.Column("sender_user_id", sa.Uuid(), nullable=False),
        sa.Column("sender_role", sa.String(length=16), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("message_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("moderation_status", sa.String(length=16), nullable=False),
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
        sa.ForeignKeyConstraint(["thread_id"], ["message_threads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_thread_id", "messages", ["thread_id"])
    op.create_index("ix_messages_sender_user_id", "messages", ["sender_user_id"])
    op.create_index("ix_messages_status", "messages", ["status"])
    op.create_index("ix_messages_moderation_status", "messages", ["moderation_status"])
    op.create_index("ix_messages_created_at", "messages", ["created_at"])

    op.create_table(
        "message_blocks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("blocker_user_id", sa.Uuid(), nullable=False),
        sa.Column("blocked_user_id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.String(length=300), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["blocker_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["blocked_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "blocker_user_id", "blocked_user_id", name="uq_message_blocks_pair"
        ),
    )
    op.create_index("ix_message_blocks_blocker_user_id", "message_blocks", ["blocker_user_id"])
    op.create_index("ix_message_blocks_blocked_user_id", "message_blocks", ["blocked_user_id"])

    op.create_table(
        "message_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("thread_id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=True),
        sa.Column("reporter_user_id", sa.Uuid(), nullable=False),
        sa.Column("reported_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=120), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("resolved_by_user_id", sa.Uuid(), nullable=True),
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
        sa.ForeignKeyConstraint(["thread_id"], ["message_threads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reported_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_message_reports_thread_id", "message_reports", ["thread_id"])
    op.create_index("ix_message_reports_status", "message_reports", ["status"])

    op.create_table(
        "in_app_notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.String(length=240), nullable=False),
        sa.Column("link_path", sa.String(length=300), nullable=True),
        sa.Column("thread_id", sa.Uuid(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["thread_id"], ["message_threads.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_in_app_notifications_user_id", "in_app_notifications", ["user_id"])
    op.create_index("ix_in_app_notifications_kind", "in_app_notifications", ["kind"])
    op.create_index(
        "ix_in_app_notifications_created_at", "in_app_notifications", ["created_at"]
    )


def downgrade() -> None:
    op.drop_table("in_app_notifications")
    op.drop_table("message_reports")
    op.drop_table("message_blocks")
    op.drop_table("messages")
    op.drop_table("message_threads")
    op.drop_table("message_settings")
