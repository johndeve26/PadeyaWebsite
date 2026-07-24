"""Fan Connect settings/connections + fan_fan message threads.

Revision ID: 20260718_0050
Revises: 20260718_0049
Create Date: 2026-07-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260718_0050"
down_revision = "20260718_0049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fan_connect_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "fan_connect_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "discoverable_for_same_events",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "allow_connection_requests",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "show_shared_hosts",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "show_shared_categories",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "show_shared_public_events",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "hide_private_events_always",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
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
        sa.UniqueConstraint("user_id", name="uq_fan_connect_settings_user_id"),
    )
    op.create_index(
        op.f("ix_fan_connect_settings_user_id"),
        "fan_connect_settings",
        ["user_id"],
        unique=False,
    )

    op.add_column(
        "message_threads",
        sa.Column("fan_b_user_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        op.f("ix_message_threads_fan_b_user_id"),
        "message_threads",
        ["fan_b_user_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_message_threads_fan_b_user_id",
        "message_threads",
        "users",
        ["fan_b_user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column(
        "message_threads",
        "host_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.create_unique_constraint(
        "uq_message_threads_fan_fan",
        "message_threads",
        ["fan_user_id", "fan_b_user_id"],
    )

    op.create_table(
        "fan_connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_low_id", sa.Uuid(), nullable=False),
        sa.Column("user_high_id", sa.Uuid(), nullable=False),
        sa.Column("requester_user_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("context_event_id", sa.Uuid(), nullable=True),
        sa.Column("message", sa.String(length=280), nullable=True),
        sa.Column("message_thread_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["context_event_id"], ["events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["message_thread_id"], ["message_threads.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requester_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_high_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_low_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_low_id", "user_high_id", name="uq_fan_connections_pair"),
    )
    op.create_index(
        op.f("ix_fan_connections_user_low_id"),
        "fan_connections",
        ["user_low_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fan_connections_user_high_id"),
        "fan_connections",
        ["user_high_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fan_connections_requester_user_id"),
        "fan_connections",
        ["requester_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fan_connections_recipient_user_id"),
        "fan_connections",
        ["recipient_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fan_connections_status"),
        "fan_connections",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("fan_connections")
    op.drop_constraint("uq_message_threads_fan_fan", "message_threads", type_="unique")
    op.drop_constraint(
        "fk_message_threads_fan_b_user_id", "message_threads", type_="foreignkey"
    )
    op.drop_index(op.f("ix_message_threads_fan_b_user_id"), table_name="message_threads")
    op.drop_column("message_threads", "fan_b_user_id")
    op.alter_column(
        "message_threads",
        "host_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.drop_table("fan_connect_settings")
