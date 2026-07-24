"""Add requires_vip and drop_live_notified_at for post-event merch drops.

Revision ID: 20260718_0049
Revises: 20260718_0048
Create Date: 2026-07-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260718_0049"
down_revision = "20260718_0048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "event_merch_products",
        sa.Column(
            "requires_vip",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "event_merch_products",
        sa.Column("drop_live_notified_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("event_merch_products", "drop_live_notified_at")
    op.drop_column("event_merch_products", "requires_vip")
