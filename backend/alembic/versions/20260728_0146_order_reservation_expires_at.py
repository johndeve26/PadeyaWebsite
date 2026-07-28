"""Add orders.reservation_expires_at for pending inventory holds.

Revision ID: 20260728_0146
Revises: 20260727_0145
Create Date: 2026-07-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260728_0146"
down_revision = "20260727_0145"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("reservation_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_orders_reservation_expires_at",
        "orders",
        ["reservation_expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_orders_reservation_expires_at", table_name="orders")
    op.drop_column("orders", "reservation_expires_at")
