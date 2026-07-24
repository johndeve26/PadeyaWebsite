"""Add description and currency to merch_discount_codes.

Revision ID: 20260718_0048
Revises: 20260718_0047
Create Date: 2026-07-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260718_0048"
down_revision = "20260718_0047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "merch_discount_codes",
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.add_column(
        "merch_discount_codes",
        sa.Column("currency", sa.String(length=8), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("merch_discount_codes", "currency")
    op.drop_column("merch_discount_codes", "description")
