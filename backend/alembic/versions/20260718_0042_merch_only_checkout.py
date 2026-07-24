"""Allow host-gated merch-only checkout on events.

Revision ID: 20260718_0042
Revises: 20260718_0041
Create Date: 2026-07-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260718_0042"
down_revision = "20260718_0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column(
            "allow_merch_only_checkout",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("events", "allow_merch_only_checkout")
