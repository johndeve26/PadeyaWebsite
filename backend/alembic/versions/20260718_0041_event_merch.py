"""Event-linked merchandise: products, variants, fulfillments; order_items polymorphic.

Revision ID: 20260718_0041
Revises: 20260718_0040
Create Date: 2026-07-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260718_0041"
down_revision = "20260718_0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "event_merch_products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("base_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), server_default="NGN", nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("pickup_instructions", sa.String(length=500), nullable=True),
        sa.Column("max_per_order", sa.Integer(), nullable=True),
        sa.Column(
            "restock_on_refund",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "slug", name="uq_event_merch_products_event_slug"),
    )
    op.create_index("ix_event_merch_products_event_id", "event_merch_products", ["event_id"])
    op.create_index("ix_event_merch_products_host_id", "event_merch_products", ["host_id"])
    op.create_index("ix_event_merch_products_status", "event_merch_products", ["status"])

    op.create_table(
        "event_merch_variants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("sku", sa.String(length=80), nullable=True),
        sa.Column("size", sa.String(length=40), nullable=True),
        sa.Column("color", sa.String(length=40), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("inventory_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["product_id"], ["event_merch_products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "label", name="uq_event_merch_variants_product_label"),
    )
    op.create_index("ix_event_merch_variants_product_id", "event_merch_variants", ["product_id"])
    op.create_index("ix_event_merch_variants_status", "event_merch_variants", ["status"])

    op.add_column(
        "order_items",
        sa.Column("item_kind", sa.String(length=16), server_default="ticket", nullable=False),
    )
    op.alter_column(
        "order_items",
        "ticket_type_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.alter_column(
        "order_items",
        "ticket_type_name",
        existing_type=sa.String(length=160),
        nullable=True,
    )
    op.add_column("order_items", sa.Column("merch_product_id", sa.Uuid(), nullable=True))
    op.add_column("order_items", sa.Column("merch_variant_id", sa.Uuid(), nullable=True))
    op.add_column(
        "order_items",
        sa.Column("product_name", sa.String(length=160), nullable=True),
    )
    op.add_column(
        "order_items",
        sa.Column("variant_label", sa.String(length=120), nullable=True),
    )
    op.create_foreign_key(
        "fk_order_items_merch_product_id",
        "order_items",
        "event_merch_products",
        ["merch_product_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_order_items_merch_variant_id",
        "order_items",
        "event_merch_variants",
        ["merch_variant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_order_items_item_kind", "order_items", ["item_kind"])
    op.create_index("ix_order_items_merch_variant_id", "order_items", ["merch_variant_id"])

    op.create_table(
        "merch_fulfillments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("order_item_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("buyer_user_id", sa.Uuid(), nullable=False),
        sa.Column("merch_variant_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="awaiting_pickup",
            nullable=False,
        ),
        sa.Column("pickup_code", sa.String(length=40), nullable=False),
        sa.Column("pickup_instructions_snapshot", sa.String(length=500), nullable=True),
        sa.Column("product_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("variant_label_snapshot", sa.String(length=120), nullable=False),
        sa.Column("fulfilled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fulfilled_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_item_id"], ["order_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buyer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["merch_variant_id"], ["event_merch_variants.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["fulfilled_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pickup_code", name="uq_merch_fulfillments_pickup_code"),
        sa.UniqueConstraint("order_item_id", name="uq_merch_fulfillments_order_item"),
    )
    op.create_index("ix_merch_fulfillments_event_id", "merch_fulfillments", ["event_id"])
    op.create_index("ix_merch_fulfillments_host_id", "merch_fulfillments", ["host_id"])
    op.create_index("ix_merch_fulfillments_buyer_user_id", "merch_fulfillments", ["buyer_user_id"])
    op.create_index("ix_merch_fulfillments_status", "merch_fulfillments", ["status"])
    op.create_index("ix_merch_fulfillments_order_id", "merch_fulfillments", ["order_id"])


def downgrade() -> None:
    op.drop_table("merch_fulfillments")
    op.drop_index("ix_order_items_merch_variant_id", table_name="order_items")
    op.drop_index("ix_order_items_item_kind", table_name="order_items")
    op.drop_constraint("fk_order_items_merch_variant_id", "order_items", type_="foreignkey")
    op.drop_constraint("fk_order_items_merch_product_id", "order_items", type_="foreignkey")
    op.drop_column("order_items", "variant_label")
    op.drop_column("order_items", "product_name")
    op.drop_column("order_items", "merch_variant_id")
    op.drop_column("order_items", "merch_product_id")
    op.alter_column(
        "order_items",
        "ticket_type_name",
        existing_type=sa.String(length=160),
        nullable=False,
    )
    op.alter_column(
        "order_items",
        "ticket_type_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.drop_column("order_items", "item_kind")
    op.drop_table("event_merch_variants")
    op.drop_table("event_merch_products")
