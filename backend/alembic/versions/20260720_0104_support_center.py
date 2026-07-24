"""Alembic: support center expansion — tickets fields, attachments, events, settings."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260720_0104"
down_revision = "20260720_0103"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Expand support_cases for visitor/public tickets + host context
    op.add_column(
        "support_cases",
        sa.Column("requester_email", sa.String(length=320), nullable=True),
    )
    op.add_column(
        "support_cases",
        sa.Column("requester_name", sa.String(length=160), nullable=True),
    )
    op.add_column(
        "support_cases",
        sa.Column(
            "requester_context",
            sa.String(length=32),
            nullable=False,
            server_default="fan",
        ),
    )
    op.add_column(
        "support_cases",
        sa.Column("related_host_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "support_cases",
        sa.Column("public_token", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_support_cases_requester_email", "support_cases", ["requester_email"])
    op.create_index("ix_support_cases_public_token", "support_cases", ["public_token"], unique=True)
    op.create_index("ix_support_cases_related_host_id", "support_cases", ["related_host_id"])
    op.create_foreign_key(
        "fk_support_cases_related_host_id",
        "support_cases",
        "hosts",
        ["related_host_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Allow visitor tickets without a user account
    op.alter_column(
        "support_cases",
        "requester_user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    # Allow visitor messages without author user
    op.alter_column(
        "support_messages",
        "author_user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.add_column(
        "support_messages",
        sa.Column("author_label", sa.String(length=160), nullable=True),
    )

    # Normalize in_progress → pending
    op.execute(
        "UPDATE support_cases SET status = 'pending' WHERE status = 'in_progress'"
    )

    op.create_table(
        "support_ticket_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("support_cases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "message_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("support_messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "uploaded_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("is_internal", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "support_ticket_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("support_cases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.String(length=400), nullable=False),
        sa.Column("meta_json", sa.Text(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "support_ticket_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("support_cases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "assignee_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "assigned_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("note", sa.String(length=400), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "support_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(length=64), unique=True, nullable=False),
        sa.Column("value_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Backfill emails/names from users where possible
    op.execute(
        """
        UPDATE support_cases c
        SET requester_email = u.email,
            requester_name = u.full_name
        FROM users u
        WHERE c.requester_user_id = u.id
          AND c.requester_email IS NULL
        """
    )


def downgrade() -> None:
    op.drop_table("support_settings")
    op.drop_table("support_ticket_assignments")
    op.drop_table("support_ticket_events")
    op.drop_table("support_ticket_attachments")
    op.drop_constraint("fk_support_cases_related_host_id", "support_cases", type_="foreignkey")
    op.drop_index("ix_support_cases_related_host_id", table_name="support_cases")
    op.drop_index("ix_support_cases_public_token", table_name="support_cases")
    op.drop_index("ix_support_cases_requester_email", table_name="support_cases")
    op.drop_column("support_messages", "author_label")
    op.alter_column(
        "support_messages",
        "author_user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_column("support_cases", "public_token")
    op.drop_column("support_cases", "related_host_id")
    op.drop_column("support_cases", "requester_context")
    op.drop_column("support_cases", "requester_name")
    op.drop_column("support_cases", "requester_email")
    op.alter_column(
        "support_cases",
        "requester_user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.execute(
        "UPDATE support_cases SET status = 'in_progress' WHERE status = 'pending'"
    )
