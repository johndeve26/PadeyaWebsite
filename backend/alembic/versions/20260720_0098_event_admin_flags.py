"""Event admin flag columns for moderation.

Revision ID: 20260720_0098
Revises: 20260720_0097
Create Date: 2026-07-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260720_0098"
down_revision = "20260720_0097"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("events") as batch:
        batch.add_column(
            sa.Column("admin_flagged_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(sa.Column("admin_flag_reason", sa.Text(), nullable=True))
        batch.add_column(
            sa.Column("admin_flagged_by_user_id", sa.Uuid(), nullable=True)
        )
        batch.create_index(
            "ix_events_admin_flagged_at", ["admin_flagged_at"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("events") as batch:
        batch.drop_index("ix_events_admin_flagged_at")
        batch.drop_column("admin_flagged_by_user_id")
        batch.drop_column("admin_flag_reason")
        batch.drop_column("admin_flagged_at")
