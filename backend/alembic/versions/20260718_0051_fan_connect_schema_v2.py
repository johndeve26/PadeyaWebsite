"""Fan Connect schema v2 — settings, connections, blocks, reports, suggestions.

Revision ID: 20260718_0051
Revises: 20260718_0050
Create Date: 2026-07-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260718_0051"
down_revision = "20260718_0050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- settings ---
    op.add_column(
        "fan_connect_settings",
        sa.Column(
            "discoverable_for_similar_interests",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "fan_connect_settings",
        sa.Column(
            "show_public_city",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "fan_connect_settings",
        sa.Column(
            "request_policy",
            sa.String(length=32),
            server_default="same_event",
            nullable=False,
        ),
    )

    # --- connections: rename / add columns ---
    op.add_column(
        "fan_connections",
        sa.Column("score", sa.Float(), server_default="0", nullable=False),
    )
    op.add_column(
        "fan_connections",
        sa.Column("reasons_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "fan_connections",
        sa.Column("related_event_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "fan_connections",
        sa.Column("related_host_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "fan_connections",
        sa.Column("request_message", sa.String(length=280), nullable=True),
    )
    op.add_column(
        "fan_connections",
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "fan_connections",
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "fan_connections",
        sa.Column("declined_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "fan_connections",
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Copy legacy columns into new names where present
    op.execute(
        """
        UPDATE fan_connections
        SET related_event_id = context_event_id
        WHERE context_event_id IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE fan_connections
        SET request_message = message
        WHERE message IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE fan_connections
        SET requested_at = created_at
        WHERE requested_at IS NULL
        """
    )
    op.execute(
        """
        UPDATE fan_connections
        SET accepted_at = responded_at
        WHERE status = 'accepted' AND responded_at IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE fan_connections
        SET declined_at = responded_at
        WHERE status = 'declined' AND responded_at IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE fan_connections
        SET removed_at = COALESCE(archived_at, responded_at)
        WHERE status IN ('cancelled', 'withdrawn')
        """
    )
    # Map legacy statuses → v2
    op.execute("UPDATE fan_connections SET status = 'request_sent' WHERE status = 'pending'")
    op.execute("UPDATE fan_connections SET status = 'connected' WHERE status = 'accepted'")
    op.execute(
        "UPDATE fan_connections SET status = 'removed' WHERE status IN ('cancelled', 'withdrawn')"
    )

    op.create_foreign_key(
        "fk_fan_connections_related_event_id",
        "fan_connections",
        "events",
        ["related_event_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_fan_connections_related_host_id",
        "fan_connections",
        "hosts",
        ["related_host_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.drop_constraint(
        "fan_connections_context_event_id_fkey",
        "fan_connections",
        type_="foreignkey",
    )
    op.drop_column("fan_connections", "context_event_id")
    op.drop_column("fan_connections", "message")
    op.drop_column("fan_connections", "responded_at")
    op.drop_column("fan_connections", "archived_at")

    # --- blocks ---
    op.create_table(
        "fan_connection_blocks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("blocker_user_id", sa.Uuid(), nullable=False),
        sa.Column("blocked_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=300), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["blocked_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["blocker_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "blocker_user_id",
            "blocked_user_id",
            name="uq_fan_connection_blocks_pair",
        ),
    )
    op.create_index(
        op.f("ix_fan_connection_blocks_blocker_user_id"),
        "fan_connection_blocks",
        ["blocker_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fan_connection_blocks_blocked_user_id"),
        "fan_connection_blocks",
        ["blocked_user_id"],
        unique=False,
    )

    # --- reports ---
    op.create_table(
        "fan_connection_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reporter_user_id", sa.Uuid(), nullable=False),
        sa.Column("reported_user_id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=True),
        sa.Column("thread_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.String(length=120), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("admin_notes", sa.Text(), nullable=True),
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
            ["connection_id"], ["fan_connections.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["reported_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["reporter_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["thread_id"], ["message_threads.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_fan_connection_reports_reporter_user_id"),
        "fan_connection_reports",
        ["reporter_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fan_connection_reports_reported_user_id"),
        "fan_connection_reports",
        ["reported_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fan_connection_reports_status"),
        "fan_connection_reports",
        ["status"],
        unique=False,
    )

    # --- suggestions cache ---
    op.create_table(
        "fan_connect_suggestions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("suggested_user_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Float(), server_default="0", nullable=False),
        sa.Column("reasons_json", sa.JSON(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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
            ["suggested_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "suggested_user_id",
            name="uq_fan_connect_suggestions_pair",
        ),
    )
    op.create_index(
        op.f("ix_fan_connect_suggestions_user_id"),
        "fan_connect_suggestions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fan_connect_suggestions_suggested_user_id"),
        "fan_connect_suggestions",
        ["suggested_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fan_connect_suggestions_expires_at"),
        "fan_connect_suggestions",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("fan_connect_suggestions")
    op.drop_table("fan_connection_reports")
    op.drop_table("fan_connection_blocks")

    op.add_column(
        "fan_connections",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "fan_connections",
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "fan_connections",
        sa.Column("message", sa.String(length=280), nullable=True),
    )
    op.add_column(
        "fan_connections",
        sa.Column("context_event_id", sa.Uuid(), nullable=True),
    )
    op.execute(
        """
        UPDATE fan_connections
        SET context_event_id = related_event_id, message = request_message,
            responded_at = COALESCE(accepted_at, declined_at, removed_at)
        """
    )
    op.execute(
        "UPDATE fan_connections SET status = 'pending' WHERE status = 'request_sent'"
    )
    op.execute(
        "UPDATE fan_connections SET status = 'accepted' WHERE status = 'connected'"
    )
    op.execute(
        "UPDATE fan_connections SET status = 'cancelled' WHERE status = 'removed'"
    )
    op.create_foreign_key(
        "fan_connections_context_event_id_fkey",
        "fan_connections",
        "events",
        ["context_event_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_constraint(
        "fk_fan_connections_related_host_id", "fan_connections", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_fan_connections_related_event_id", "fan_connections", type_="foreignkey"
    )
    op.drop_column("fan_connections", "removed_at")
    op.drop_column("fan_connections", "declined_at")
    op.drop_column("fan_connections", "accepted_at")
    op.drop_column("fan_connections", "requested_at")
    op.drop_column("fan_connections", "request_message")
    op.drop_column("fan_connections", "related_host_id")
    op.drop_column("fan_connections", "related_event_id")
    op.drop_column("fan_connections", "reasons_json")
    op.drop_column("fan_connections", "score")

    op.drop_column("fan_connect_settings", "request_policy")
    op.drop_column("fan_connect_settings", "show_public_city")
    op.drop_column("fan_connect_settings", "discoverable_for_similar_interests")
