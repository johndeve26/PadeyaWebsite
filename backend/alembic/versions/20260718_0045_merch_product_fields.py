"""Merch product display/fulfillment fields for host create form.

Revision ID: 20260718_0045
Revises: 20260718_0044
Create Date: 2026-07-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260718_0045"
down_revision = "20260718_0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "event_merch_products",
        sa.Column(
            "show_on_event_page",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "event_merch_products",
        sa.Column("pickup_location_label", sa.String(length=160), nullable=True),
    )
    op.add_column(
        "event_merch_products",
        sa.Column("pickup_time_window", sa.String(length=160), nullable=True),
    )
    op.add_column(
        "event_merch_products",
        sa.Column("fulfillment_notes", sa.String(length=1000), nullable=True),
    )

    op.add_column(
        "merch_fulfillments",
        sa.Column("pickup_location_label_snapshot", sa.String(length=160), nullable=True),
    )
    op.add_column(
        "merch_fulfillments",
        sa.Column("pickup_time_window_snapshot", sa.String(length=160), nullable=True),
    )
    op.add_column(
        "merch_fulfillments",
        sa.Column("fulfillment_notes_snapshot", sa.String(length=1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("merch_fulfillments", "fulfillment_notes_snapshot")
    op.drop_column("merch_fulfillments", "pickup_time_window_snapshot")
    op.drop_column("merch_fulfillments", "pickup_location_label_snapshot")
    op.drop_column("event_merch_products", "fulfillment_notes")
    op.drop_column("event_merch_products", "pickup_time_window")
    op.drop_column("event_merch_products", "pickup_location_label")
    op.drop_column("event_merch_products", "show_on_event_page")
