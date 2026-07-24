"""Add security lock columns on users for impersonation / account safety.

Revision ID: 20260720_0088
Revises: 20260719_0087
Create Date: 2026-07-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260720_0088"
down_revision = "20260719_0087"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("security_locked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("security_lock_reason", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "security_lock_reason")
    op.drop_column("users", "security_locked_at")
