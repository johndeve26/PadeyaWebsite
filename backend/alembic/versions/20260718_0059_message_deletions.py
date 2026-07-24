"""Per-viewer message deletions (delete for me).

Revision ID: 20260718_0059
Revises: 20260718_0058
Create Date: 2026-07-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260718_0059"
down_revision = "20260718_0058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "message_deletions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("message_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("delete_scope", sa.String(32), nullable=False),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["message_id"], ["messages.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "message_id",
            "user_id",
            "delete_scope",
            name="uq_message_deletions_message_user_scope",
        ),
    )
    op.create_index(
        "ix_message_deletions_message_id", "message_deletions", ["message_id"]
    )
    op.create_index(
        "ix_message_deletions_user_id", "message_deletions", ["user_id"]
    )
    op.create_index(
        "ix_message_deletions_deleted_at", "message_deletions", ["deleted_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_message_deletions_deleted_at", table_name="message_deletions")
    op.drop_index("ix_message_deletions_user_id", table_name="message_deletions")
    op.drop_index("ix_message_deletions_message_id", table_name="message_deletions")
    op.drop_table("message_deletions")
