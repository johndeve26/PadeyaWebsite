"""Persist user active host workspace selection.

Revision ID: 20260719_0073
Revises: 20260719_0072
Create Date: 2026-07-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260719_0073"
down_revision = "20260719_0072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_active_workspaces",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(
        "ix_user_active_workspaces_host_id", "user_active_workspaces", ["host_id"]
    )


def downgrade() -> None:
    op.drop_table("user_active_workspaces")
