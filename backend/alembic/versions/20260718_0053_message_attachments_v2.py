"""Expand message_attachments + optional download audit.

Revision ID: 20260718_0053
Revises: 20260718_0052
Create Date: 2026-07-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260718_0053"
down_revision = "20260718_0052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "message_attachments",
        sa.Column("thread_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "message_attachments",
        sa.Column("safe_filename", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "message_attachments",
        sa.Column("file_extension", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "message_attachments",
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "message_attachments",
        sa.Column("width", sa.Integer(), nullable=True),
    )
    op.add_column(
        "message_attachments",
        sa.Column("height", sa.Integer(), nullable=True),
    )
    op.add_column(
        "message_attachments",
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="ready",
            nullable=False,
        ),
    )
    op.add_column(
        "message_attachments",
        sa.Column("rejection_reason", sa.String(length=300), nullable=True),
    )
    op.add_column(
        "message_attachments",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "message_attachments",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Rename content_type → mime_type, byte_size → file_size (batch-friendly).
    op.alter_column(
        "message_attachments",
        "content_type",
        new_column_name="mime_type",
        existing_type=sa.String(length=80),
        type_=sa.String(length=120),
        existing_nullable=False,
    )
    op.alter_column(
        "message_attachments",
        "byte_size",
        new_column_name="file_size",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "message_attachments",
        "storage_key",
        existing_type=sa.String(length=500),
        nullable=True,
    )
    op.alter_column(
        "message_attachments",
        "url",
        existing_type=sa.String(length=800),
        nullable=True,
    )

    # Backfill thread_id from bound messages; drop orphan staged rows.
    op.execute(
        """
        UPDATE message_attachments AS a
        SET thread_id = m.thread_id
        FROM messages AS m
        WHERE a.message_id = m.id AND a.thread_id IS NULL
        """
    )
    op.execute("DELETE FROM message_attachments WHERE thread_id IS NULL")

    op.alter_column(
        "message_attachments",
        "thread_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_message_attachments_thread_id",
        "message_attachments",
        "message_threads",
        ["thread_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_message_attachments_thread_id"),
        "message_attachments",
        ["thread_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_message_attachments_status"),
        "message_attachments",
        ["status"],
        unique=False,
    )

    op.create_table(
        "message_attachment_downloads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("attachment_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "downloaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["attachment_id"],
            ["message_attachments.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_message_attachment_downloads_attachment_id"),
        "message_attachment_downloads",
        ["attachment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_message_attachment_downloads_user_id"),
        "message_attachment_downloads",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_message_attachment_downloads_user_id"),
        table_name="message_attachment_downloads",
    )
    op.drop_index(
        op.f("ix_message_attachment_downloads_attachment_id"),
        table_name="message_attachment_downloads",
    )
    op.drop_table("message_attachment_downloads")

    op.drop_index(
        op.f("ix_message_attachments_status"), table_name="message_attachments"
    )
    op.drop_index(
        op.f("ix_message_attachments_thread_id"), table_name="message_attachments"
    )
    op.drop_constraint(
        "fk_message_attachments_thread_id",
        "message_attachments",
        type_="foreignkey",
    )

    op.alter_column(
        "message_attachments",
        "mime_type",
        new_column_name="content_type",
        existing_type=sa.String(length=120),
        type_=sa.String(length=80),
        existing_nullable=False,
    )
    op.alter_column(
        "message_attachments",
        "file_size",
        new_column_name="byte_size",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "message_attachments",
        "storage_key",
        existing_type=sa.String(length=500),
        nullable=False,
    )
    op.alter_column(
        "message_attachments",
        "url",
        existing_type=sa.String(length=800),
        nullable=False,
    )

    op.drop_column("message_attachments", "deleted_at")
    op.drop_column("message_attachments", "updated_at")
    op.drop_column("message_attachments", "rejection_reason")
    op.drop_column("message_attachments", "status")
    op.drop_column("message_attachments", "height")
    op.drop_column("message_attachments", "width")
    op.drop_column("message_attachments", "checksum_sha256")
    op.drop_column("message_attachments", "file_extension")
    op.drop_column("message_attachments", "safe_filename")
    op.drop_column("message_attachments", "thread_id")
