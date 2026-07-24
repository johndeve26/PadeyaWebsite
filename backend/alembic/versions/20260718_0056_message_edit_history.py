"""Message edit metadata and history.

Revision ID: 20260718_0056
Revises: 20260718_0055
Create Date: 2026-07-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260718_0056"
down_revision = "20260718_0055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column(
            "edit_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "messages",
        sa.Column("last_edited_by_user_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_messages_last_edited_by_user_id",
        "messages",
        "users",
        ["last_edited_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_messages_last_edited_by_user_id",
        "messages",
        ["last_edited_by_user_id"],
    )

    op.create_table(
        "message_edits",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("message_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("editor_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("previous_body", sa.Text(), nullable=False),
        sa.Column("new_body", sa.Text(), nullable=False),
        sa.Column(
            "edited_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["message_id"], ["messages.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["editor_user_id"], ["users.id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_message_edits_message_id", "message_edits", ["message_id"])
    op.create_index(
        "ix_message_edits_editor_user_id", "message_edits", ["editor_user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_message_edits_editor_user_id", table_name="message_edits")
    op.drop_index("ix_message_edits_message_id", table_name="message_edits")
    op.drop_table("message_edits")
    op.drop_index("ix_messages_last_edited_by_user_id", table_name="messages")
    op.drop_constraint(
        "fk_messages_last_edited_by_user_id", "messages", type_="foreignkey"
    )
    op.drop_column("messages", "last_edited_by_user_id")
    op.drop_column("messages", "edit_count")
