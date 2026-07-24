"""event memories

Revision ID: 20260716_0012
Revises: 20260716_0011
Create Date: 2026-07-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260716_0012"
down_revision: Union[str, Sequence[str], None] = "20260716_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "event_memories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("host_recap_note", sa.Text(), nullable=True),
        sa.Column("moderation_status", sa.String(length=32), nullable=False),
        sa.Column("moderation_note", sa.Text(), nullable=True),
        sa.Column("moderated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["moderated_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_event_memories_event_id"),
    )
    op.create_index("ix_event_memories_event_id", "event_memories", ["event_id"])
    op.create_index("ix_event_memories_host_id", "event_memories", ["host_id"])
    op.create_index("ix_event_memories_status", "event_memories", ["status"])
    op.create_index(
        "ix_event_memories_moderation_status",
        "event_memories",
        ["moderation_status"],
    )
    op.create_index("ix_event_memories_created_at", "event_memories", ["created_at"])

    op.create_table(
        "event_memory_media",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("memory_id", sa.Uuid(), nullable=False),
        sa.Column("media_type", sa.String(length=64), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=True),
        sa.Column("label", sa.String(length=160), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["memory_id"], ["event_memories.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_event_memory_media_memory_id", "event_memory_media", ["memory_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_event_memory_media_memory_id", table_name="event_memory_media")
    op.drop_table("event_memory_media")
    op.drop_index("ix_event_memories_created_at", table_name="event_memories")
    op.drop_index("ix_event_memories_moderation_status", table_name="event_memories")
    op.drop_index("ix_event_memories_status", table_name="event_memories")
    op.drop_index("ix_event_memories_host_id", table_name="event_memories")
    op.drop_index("ix_event_memories_event_id", table_name="event_memories")
    op.drop_table("event_memories")
