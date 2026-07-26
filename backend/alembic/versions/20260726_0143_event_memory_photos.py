"""Add photo-contribution fields to event memories.

Revision ID: 20260726_0143
Revises: 20260726_0142
Create Date: 2026-07-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260726_0143"
down_revision = "20260726_0142"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "event_memories",
        sa.Column("external_gallery_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "event_memories",
        sa.Column("external_gallery_label", sa.String(length=64), nullable=True),
    )

    op.add_column(
        "event_memory_media",
        sa.Column("caption", sa.String(length=280), nullable=True),
    )
    op.add_column(
        "event_memory_media",
        sa.Column("uploader_user_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.add_column(
        "event_memory_media",
        sa.Column(
            "uploader_role",
            sa.String(length=16),
            nullable=False,
            server_default="host",
        ),
    )
    op.add_column(
        "event_memory_media",
        sa.Column("width", sa.Integer(), nullable=True),
    )
    op.add_column(
        "event_memory_media",
        sa.Column("height", sa.Integer(), nullable=True),
    )
    op.add_column(
        "event_memory_media",
        sa.Column("mime_type", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "event_memory_media",
        sa.Column("size_bytes", sa.Integer(), nullable=True),
    )
    op.add_column(
        "event_memory_media",
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "event_memory_media",
        sa.Column(
            "is_cover",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "event_memory_media",
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="active",
        ),
    )
    op.add_column(
        "event_memory_media",
        sa.Column("hidden_by", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "event_memory_media",
        sa.Column("hidden_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "event_memory_media",
        sa.Column("moderation_note", sa.Text(), nullable=True),
    )
    op.add_column(
        "event_memory_media",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_foreign_key(
        "fk_event_memory_media_uploader_user_id",
        "event_memory_media",
        "users",
        ["uploader_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_event_memory_media_uploader_user_id",
        "event_memory_media",
        ["uploader_user_id"],
    )
    op.create_index(
        "ix_event_memory_media_uploader_role",
        "event_memory_media",
        ["uploader_role"],
    )
    op.create_index(
        "ix_event_memory_media_status",
        "event_memory_media",
        ["status"],
    )
    op.create_index(
        "ix_event_memory_media_memory_status_created",
        "event_memory_media",
        ["memory_id", "status", "created_at"],
    )
    op.create_index(
        "ix_event_memory_media_uploader_memory_status",
        "event_memory_media",
        ["uploader_user_id", "memory_id", "status"],
    )

    # Backfill: copy label → caption; set host uploader from event host user.
    op.execute(
        """
        UPDATE event_memory_media
        SET caption = label
        WHERE caption IS NULL AND label IS NOT NULL AND btrim(label) <> ''
        """
    )
    op.execute(
        """
        UPDATE event_memory_media AS m
        SET uploader_user_id = h.user_id,
            uploader_role = 'host',
            status = COALESCE(m.status, 'active')
        FROM event_memories AS em
        JOIN hosts AS h ON h.id = em.host_id
        WHERE m.memory_id = em.id
          AND m.uploader_user_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_event_memory_media_uploader_memory_status",
        table_name="event_memory_media",
    )
    op.drop_index(
        "ix_event_memory_media_memory_status_created",
        table_name="event_memory_media",
    )
    op.drop_index("ix_event_memory_media_status", table_name="event_memory_media")
    op.drop_index(
        "ix_event_memory_media_uploader_role", table_name="event_memory_media"
    )
    op.drop_index(
        "ix_event_memory_media_uploader_user_id", table_name="event_memory_media"
    )
    op.drop_constraint(
        "fk_event_memory_media_uploader_user_id",
        "event_memory_media",
        type_="foreignkey",
    )
    for col in (
        "updated_at",
        "moderation_note",
        "hidden_at",
        "hidden_by",
        "status",
        "is_cover",
        "thumbnail_url",
        "size_bytes",
        "mime_type",
        "height",
        "width",
        "uploader_role",
        "uploader_user_id",
        "caption",
    ):
        op.drop_column("event_memory_media", col)

    op.drop_column("event_memories", "external_gallery_label")
    op.drop_column("event_memories", "external_gallery_url")
