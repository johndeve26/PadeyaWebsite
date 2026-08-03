"""Refund line allocations for referral commission reversal.

Revision ID: 20260803_0217
Revises: 20260803_0216
Create Date: 2026-08-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260803_0217"
down_revision = "20260803_0216"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "refund_requests",
        sa.Column(
            "line_allocations",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
    )
    op.add_column(
        "refund_requests",
        sa.Column(
            "requires_referral_refund_allocation",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("refund_requests", "requires_referral_refund_allocation")
    op.drop_column("refund_requests", "line_allocations")
