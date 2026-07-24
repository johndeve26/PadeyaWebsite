"""Message reply, pins, and stars for chat features.

Revision ID: 20260718_0055
Revises: 20260718_0054
Create Date: 2026-07-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260718_0055"
down_revision = "20260718_0054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("reply_to_message_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_messages_reply_to_message_id",
        "messages",
        "messages",
        ["reply_to_message_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_messages_reply_to_message_id",
        "messages",
        ["reply_to_message_id"],
    )

    op.create_table(
        "message_pins",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("thread_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("message_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("pinned_by_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "pinned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["thread_id"], ["message_threads.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["message_id"], ["messages.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["pinned_by_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("message_id", name="uq_message_pins_message_id"),
    )
    op.create_index("ix_message_pins_thread_id", "message_pins", ["thread_id"])
    op.create_index("ix_message_pins_message_id", "message_pins", ["message_id"])
    op.create_index(
        "ix_message_pins_pinned_by_user_id",
        "message_pins",
        ["pinned_by_user_id"],
    )

    op.create_table(
        "message_stars",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("message_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["message_id"], ["messages.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "user_id", "message_id", name="uq_message_stars_user_message"
        ),
    )
    op.create_index("ix_message_stars_user_id", "message_stars", ["user_id"])
    op.create_index(
        "ix_message_stars_message_id", "message_stars", ["message_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_message_stars_message_id", table_name="message_stars")
    op.drop_index("ix_message_stars_user_id", table_name="message_stars")
    op.drop_table("message_stars")
    op.drop_index(
        "ix_message_pins_pinned_by_user_id", table_name="message_pins"
    )
    op.drop_index("ix_message_pins_message_id", table_name="message_pins")
    op.drop_index("ix_message_pins_thread_id", table_name="message_pins")
    op.drop_table("message_pins")
    op.drop_index("ix_messages_reply_to_message_id", table_name="messages")
    op.drop_constraint(
        "fk_messages_reply_to_message_id", "messages", type_="foreignkey"
    )
    op.drop_column("messages", "reply_to_message_id")
