"""Alembic: order fee summary columns for checkout.

Revision ID: 20260721_0113
Revises: 20260721_0112
Create Date: 2026-07-21

Persists buyer/host fee totals on orders so Paystack amount, webhook verify,
and host ledger credits stay consistent with fee snapshots.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260721_0113"
down_revision = "20260721_0112"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "buyer_fee_total",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "host_fee_total",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "processing_fee_total",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "platform_revenue_total",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "host_net_estimate",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("orders", "host_net_estimate")
    op.drop_column("orders", "platform_revenue_total")
    op.drop_column("orders", "processing_fee_total")
    op.drop_column("orders", "host_fee_total")
    op.drop_column("orders", "buyer_fee_total")
