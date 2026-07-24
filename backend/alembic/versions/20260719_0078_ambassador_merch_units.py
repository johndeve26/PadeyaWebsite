"""Track merch units on ambassador sales.

Revision ID: 20260719_0078
Revises: 20260719_0077
Create Date: 2026-07-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260719_0078"
down_revision = "20260719_0077"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ambassador_sales",
        sa.Column(
            "merch_units_sold",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("ambassador_sales", "merch_units_sold")
