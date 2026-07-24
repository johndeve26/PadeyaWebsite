"""Enrich merch catalog/variant fields + fulfillment event log.

Reuses existing orders / order_items / payments / merch_fulfillments.
Does not create a parallel event_merch_order_items table.

Revision ID: 20260718_0044
Revises: 20260718_0043
Create Date: 2026-07-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260718_0044"
down_revision = "20260718_0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- event_merch_products enrichment ---
    op.add_column(
        "event_merch_products",
        sa.Column("short_description", sa.String(length=280), nullable=True),
    )
    op.add_column(
        "event_merch_products",
        sa.Column("product_type", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "event_merch_products",
        sa.Column(
            "gallery_urls",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
    )
    op.add_column(
        "event_merch_products",
        sa.Column("sales_start_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "event_merch_products",
        sa.Column("sales_end_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "event_merch_products",
        sa.Column(
            "is_featured",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "event_merch_products",
        sa.Column(
            "requires_ticket",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "event_merch_products",
        sa.Column("max_per_buyer", sa.Integer(), nullable=True),
    )

    # --- event_merch_variants enrichment ---
    op.add_column(
        "event_merch_variants",
        sa.Column("option_1_name", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "event_merch_variants",
        sa.Column("option_1_value", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "event_merch_variants",
        sa.Column("option_2_name", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "event_merch_variants",
        sa.Column("option_2_value", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "event_merch_variants",
        sa.Column(
            "reserved_quantity",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "event_merch_variants",
        sa.Column(
            "sold_quantity",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )

    # --- reports enrichment (keep merch_product_reports name) ---
    op.add_column(
        "merch_product_reports",
        sa.Column("details", sa.Text(), nullable=True),
    )
    op.add_column(
        "merch_product_reports",
        sa.Column("admin_notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "merch_product_reports",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    # --- fulfillment event timeline ---
    op.create_table(
        "event_merch_fulfillment_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("merch_fulfillment_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("note", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["merch_fulfillment_id"],
            ["merch_fulfillments.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_event_merch_fulfillment_events_fulfillment_id",
        "event_merch_fulfillment_events",
        ["merch_fulfillment_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_event_merch_fulfillment_events_fulfillment_id",
        table_name="event_merch_fulfillment_events",
    )
    op.drop_table("event_merch_fulfillment_events")

    op.drop_column("merch_product_reports", "updated_at")
    op.drop_column("merch_product_reports", "admin_notes")
    op.drop_column("merch_product_reports", "details")

    op.drop_column("event_merch_variants", "sold_quantity")
    op.drop_column("event_merch_variants", "reserved_quantity")
    op.drop_column("event_merch_variants", "option_2_value")
    op.drop_column("event_merch_variants", "option_2_name")
    op.drop_column("event_merch_variants", "option_1_value")
    op.drop_column("event_merch_variants", "option_1_name")

    op.drop_column("event_merch_products", "max_per_buyer")
    op.drop_column("event_merch_products", "requires_ticket")
    op.drop_column("event_merch_products", "is_featured")
    op.drop_column("event_merch_products", "sales_end_at")
    op.drop_column("event_merch_products", "sales_start_at")
    op.drop_column("event_merch_products", "gallery_urls")
    op.drop_column("event_merch_products", "product_type")
    op.drop_column("event_merch_products", "short_description")
