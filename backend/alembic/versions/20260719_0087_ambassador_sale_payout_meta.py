"""Ambassador sale payout metadata for host reward-status.

Revision ID: 20260719_0087
Revises: 20260719_0086
Create Date: 2026-07-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260719_0087"
down_revision = "20260719_0086"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ambassador_sales",
        sa.Column("payout_reference", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "ambassador_sales",
        sa.Column("payout_note", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "ambassador_sales",
        sa.Column("rejection_reason", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ambassador_sales", "rejection_reason")
    op.drop_column("ambassador_sales", "payout_note")
    op.drop_column("ambassador_sales", "payout_reference")
