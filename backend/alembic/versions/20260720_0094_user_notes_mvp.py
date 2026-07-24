"""Evolve user_admin_notes to MVP note_type fields.

Revision ID: 20260720_0094
Revises: 20260720_0093
Create Date: 2026-07-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260720_0094"
down_revision = "20260720_0093"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("user_admin_notes") as batch:
        batch.alter_column(
            "author_user_id", new_column_name="created_by_admin_id"
        )
        batch.add_column(
            sa.Column(
                "note_type",
                sa.String(length=32),
                nullable=False,
                server_default="general",
            )
        )
        batch.add_column(
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.create_index(
            "ix_user_admin_notes_note_type", ["note_type"], unique=False
        )

    op.alter_column("user_admin_notes", "note_type", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("user_admin_notes") as batch:
        batch.drop_index("ix_user_admin_notes_note_type")
        batch.drop_column("updated_at")
        batch.drop_column("note_type")
        batch.alter_column(
            "created_by_admin_id", new_column_name="author_user_id"
        )
