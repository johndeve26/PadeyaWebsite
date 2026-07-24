"""Merch commerce expansion aligned with app.merch.models.

Revision ID: 20260718_0047
Revises: 20260718_0046
Create Date: 2026-07-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260718_0047"
down_revision = "20260718_0046"
branch_labels = None
depends_on = None

JSON_T = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "merch_size_charts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("product_type", sa.String(length=64), nullable=True),
        sa.Column("units", sa.String(length=16), server_default="cm", nullable=False),
        sa.Column("chart_json", JSON_T, nullable=False),
        sa.Column("fit_notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
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
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_merch_size_charts_host_id", "merch_size_charts", ["host_id"])

    op.alter_column("event_merch_products", "event_id", existing_type=sa.Uuid(), nullable=True)

    for name, col in [
        ("is_event_linked", sa.Column("is_event_linked", sa.Boolean(), server_default=sa.text("true"), nullable=False)),
        ("storefront_visibility", sa.Column("storefront_visibility", sa.String(32), server_default="event_only", nullable=False)),
        ("is_merch_only_enabled", sa.Column("is_merch_only_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False)),
        ("is_vault_exclusive", sa.Column("is_vault_exclusive", sa.Boolean(), server_default=sa.text("false"), nullable=False)),
        ("required_vault_item_id", sa.Column("required_vault_item_id", sa.Uuid(), nullable=True)),
        ("required_access_type", sa.Column("required_access_type", sa.String(40), nullable=True)),
        ("is_sponsor_branded", sa.Column("is_sponsor_branded", sa.Boolean(), server_default=sa.text("false"), nullable=False)),
        ("sponsor_id", sa.Column("sponsor_id", sa.Uuid(), nullable=True)),
        ("sponsor_brand_name", sa.Column("sponsor_brand_name", sa.String(160), nullable=True)),
        ("sponsor_logo_url", sa.Column("sponsor_logo_url", sa.String(500), nullable=True)),
        ("sponsor_description", sa.Column("sponsor_description", sa.String(500), nullable=True)),
        ("sponsor_split_type", sa.Column("sponsor_split_type", sa.String(16), nullable=True)),
        ("sponsor_split_value", sa.Column("sponsor_split_value", sa.Numeric(12, 2), nullable=True)),
        ("requires_check_in", sa.Column("requires_check_in", sa.Boolean(), server_default=sa.text("false"), nullable=False)),
        ("requires_vault_access", sa.Column("requires_vault_access", sa.Boolean(), server_default=sa.text("false"), nullable=False)),
        ("related_fan_badge_id", sa.Column("related_fan_badge_id", sa.Uuid(), nullable=True)),
        ("post_event_drop_at", sa.Column("post_event_drop_at", sa.DateTime(timezone=True), nullable=True)),
        ("pickup_enabled", sa.Column("pickup_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False)),
        ("shipping_enabled", sa.Column("shipping_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False)),
        ("print_on_demand_enabled", sa.Column("print_on_demand_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False)),
        ("size_chart_id", sa.Column("size_chart_id", sa.Uuid(), nullable=True)),
        ("low_stock_threshold", sa.Column("low_stock_threshold", sa.Integer(), server_default="5", nullable=False)),
    ]:
        op.add_column("event_merch_products", col)

    op.create_foreign_key(
        "fk_event_merch_products_size_chart_id",
        "event_merch_products",
        "merch_size_charts",
        ["size_chart_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_event_merch_products_required_vault_item_id",
        "event_merch_products",
        "vault_items",
        ["required_vault_item_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_event_merch_products_sponsor_id",
        "event_merch_products",
        "sponsors",
        ["sponsor_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_event_merch_products_storefront_visibility",
        "event_merch_products",
        ["storefront_visibility"],
    )

    op.add_column(
        "event_merch_variants",
        sa.Column("low_stock_threshold", sa.Integer(), nullable=True),
    )
    op.add_column(
        "event_merch_variants",
        sa.Column("print_on_demand_variant_ref", sa.String(120), nullable=True),
    )

    op.create_table(
        "merch_bundles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), server_default="draft", nullable=False),
        sa.Column("bundle_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(8), server_default="NGN", nullable=False),
        sa.Column("ticket_type_id", sa.Uuid(), nullable=False),
        sa.Column("merch_variant_rules", JSON_T, nullable=False),
        sa.Column("inventory_limit", sa.Integer(), nullable=True),
        sa.Column("quantity_reserved", sa.Integer(), server_default="0", nullable=False),
        sa.Column("quantity_sold", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_per_buyer", sa.Integer(), nullable=True),
        sa.Column("sales_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sales_end_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_type_id"], ["ticket_types.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "slug", name="uq_merch_bundles_event_slug"),
    )
    op.create_index("ix_merch_bundles_event_id", "merch_bundles", ["event_id"])
    op.create_index("ix_merch_bundles_host_id", "merch_bundles", ["host_id"])

    op.create_table(
        "merch_discount_codes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("discount_type", sa.String(32), nullable=False),
        sa.Column("discount_value", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("applies_to", sa.String(40), server_default="merch_only", nullable=False),
        sa.Column("product_ids", JSON_T, nullable=True),
        sa.Column("min_order_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("usage_limit", sa.Integer(), nullable=True),
        sa.Column("per_buyer_limit", sa.Integer(), nullable=True),
        sa.Column("usage_count_paid", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(32), server_default="active", nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("host_id", "code", name="uq_merch_discount_codes_host_code"),
    )
    op.create_index("ix_merch_discount_codes_host_id", "merch_discount_codes", ["host_id"])
    op.create_index("ix_merch_discount_codes_event_id", "merch_discount_codes", ["event_id"])

    op.create_table(
        "merch_discount_redemptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("discount_code_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("buyer_user_id", sa.Uuid(), nullable=False),
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(32), server_default="pending", nullable=False),
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
        sa.ForeignKeyConstraint(
            ["discount_code_id"], ["merch_discount_codes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buyer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_merch_discount_redemptions_order"),
    )
    op.create_index(
        "ix_merch_discount_redemptions_discount_code_id",
        "merch_discount_redemptions",
        ["discount_code_id"],
    )

    op.add_column("orders", sa.Column("merch_discount_code_id", sa.Uuid(), nullable=True))
    op.add_column(
        "orders", sa.Column("merch_discount_code_snapshot", sa.String(64), nullable=True)
    )
    op.add_column(
        "orders",
        sa.Column(
            "merch_discount_amount",
            sa.Numeric(12, 2),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "orders",
        sa.Column("shipping_amount", sa.Numeric(12, 2), server_default="0", nullable=False),
    )
    op.add_column("orders", sa.Column("shipping_address_id", sa.Uuid(), nullable=True))
    op.add_column("orders", sa.Column("fulfillment_method", sa.String(32), nullable=True))
    op.create_foreign_key(
        "fk_orders_merch_discount_code_id",
        "orders",
        "merch_discount_codes",
        ["merch_discount_code_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("order_items", sa.Column("bundle_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_order_items_bundle_id",
        "order_items",
        "merch_bundles",
        ["bundle_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "merch_shipping_zones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("country", sa.String(80), nullable=False),
        sa.Column("state", sa.String(80), nullable=True),
        sa.Column("city", sa.String(80), nullable=True),
        sa.Column("flat_fee", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("currency", sa.String(8), server_default="NGN", nullable=False),
        sa.Column("status", sa.String(32), server_default="active", nullable=False),
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
    )
    op.create_index("ix_merch_shipping_zones_host_id", "merch_shipping_zones", ["host_id"])

    op.create_table(
        "merch_shipping_addresses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("buyer_user_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_name_enc", sa.Text(), nullable=False),
        sa.Column("phone_enc", sa.Text(), nullable=False),
        sa.Column("line1_enc", sa.Text(), nullable=False),
        sa.Column("line2_enc", sa.Text(), nullable=True),
        sa.Column("notes_enc", sa.Text(), nullable=True),
        sa.Column("city", sa.String(80), nullable=False),
        sa.Column("state", sa.String(80), nullable=False),
        sa.Column("country", sa.String(80), nullable=False),
        sa.Column("postal_code", sa.String(32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buyer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_merch_shipping_addresses_order"),
    )
    op.create_index(
        "ix_merch_shipping_addresses_buyer_user_id",
        "merch_shipping_addresses",
        ["buyer_user_id"],
    )

    op.add_column(
        "merch_fulfillments",
        sa.Column("fulfillment_method", sa.String(32), server_default="pickup", nullable=False),
    )
    op.add_column(
        "merch_fulfillments", sa.Column("pickup_qr_token_hash", sa.String(128), nullable=True)
    )
    op.alter_column("merch_fulfillments", "event_id", existing_type=sa.Uuid(), nullable=True)
    op.add_column("merch_fulfillments", sa.Column("shipping_address_id", sa.Uuid(), nullable=True))
    op.add_column("merch_fulfillments", sa.Column("tracking_number", sa.String(120), nullable=True))
    op.add_column("merch_fulfillments", sa.Column("carrier", sa.String(80), nullable=True))
    op.add_column("merch_fulfillments", sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "merch_fulfillments", sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("merch_fulfillments", sa.Column("pod_job_id", sa.Uuid(), nullable=True))
    op.add_column("merch_fulfillments", sa.Column("bundle_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_merch_fulfillments_shipping_address_id",
        "merch_fulfillments",
        "merch_shipping_addresses",
        ["shipping_address_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_merch_fulfillments_bundle_id",
        "merch_fulfillments",
        "merch_bundles",
        ["bundle_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "merch_carts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("buyer_user_id", sa.Uuid(), nullable=True),
        sa.Column("anonymous_id", sa.String(64), nullable=True),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("host_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(32), server_default="active", nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column(
            "last_activity_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("recovery_sent_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["buyer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_merch_carts_buyer_user_id", "merch_carts", ["buyer_user_id"])
    op.create_index("ix_merch_carts_anonymous_id", "merch_carts", ["anonymous_id"])
    op.create_index("ix_merch_carts_status", "merch_carts", ["status"])

    op.create_table(
        "merch_cart_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cart_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("variant_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_snapshot", sa.Numeric(12, 2), nullable=False),
        sa.Column("product_name_snapshot", sa.String(160), nullable=False),
        sa.Column("variant_label_snapshot", sa.String(120), nullable=False),
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
        sa.ForeignKeyConstraint(["cart_id"], ["merch_carts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["product_id"], ["event_merch_products.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"], ["event_merch_variants.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cart_id", "variant_id", name="uq_merch_cart_items_cart_variant"),
    )
    op.create_index("ix_merch_cart_items_cart_id", "merch_cart_items", ["cart_id"])

    op.create_table(
        "merch_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("order_item_id", sa.Uuid(), nullable=False),
        sa.Column("buyer_user_id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), server_default="published", nullable=False),
        sa.Column("host_reply", sa.Text(), nullable=True),
        sa.Column("host_replied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("admin_note", sa.String(1000), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["product_id"], ["event_merch_products.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["order_item_id"], ["order_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buyer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_item_id", name="uq_merch_reviews_order_item"),
    )
    op.create_index("ix_merch_reviews_product_id", "merch_reviews", ["product_id"])
    op.create_index("ix_merch_reviews_host_id", "merch_reviews", ["host_id"])
    op.create_index("ix_merch_reviews_status", "merch_reviews", ["status"])

    op.create_table(
        "merch_stock_alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("variant_id", sa.Uuid(), nullable=True),
        sa.Column("alert_type", sa.String(32), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=True),
        sa.Column("available_snapshot", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(32), server_default="open", nullable=False),
        sa.Column(
            "triggered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["product_id"], ["event_merch_products.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"], ["event_merch_variants.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_merch_stock_alerts_host_id", "merch_stock_alerts", ["host_id"])
    op.create_index("ix_merch_stock_alerts_alert_type", "merch_stock_alerts", ["alert_type"])
    op.create_index("ix_merch_stock_alerts_status", "merch_stock_alerts", ["status"])

    op.create_table(
        "merch_revenue_splits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("order_item_id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("currency", sa.String(8), server_default="NGN", nullable=False),
        sa.Column("gross_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("platform_amount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("host_amount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("sponsor_amount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("print_partner_amount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("fulfillment_method", sa.String(32), nullable=True),
        sa.Column(
            "is_sponsor_branded",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("bundle_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(32), server_default="payable", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_item_id"], ["order_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["product_id"], ["event_merch_products.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["bundle_id"], ["merch_bundles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_item_id", name="uq_merch_revenue_splits_order_item"),
    )
    op.create_index("ix_merch_revenue_splits_host_id", "merch_revenue_splits", ["host_id"])
    op.create_index("ix_merch_revenue_splits_order_id", "merch_revenue_splits", ["order_id"])

    op.create_table(
        "merch_print_on_demand_integrations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(40), server_default="manual", nullable=False),
        sa.Column("status", sa.String(32), server_default="disabled", nullable=False),
        sa.Column("provider_store_ref", sa.String(160), nullable=True),
        sa.Column("credentials_enc", sa.Text(), nullable=True),
        sa.Column("sync_note", sa.String(500), nullable=True),
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
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "host_id", "provider", name="uq_merch_pod_integrations_host_provider"
        ),
    )
    op.create_index(
        "ix_merch_print_on_demand_integrations_host_id",
        "merch_print_on_demand_integrations",
        ["host_id"],
    )

    op.create_table(
        "merch_pod_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("order_item_id", sa.Uuid(), nullable=False),
        sa.Column("merch_fulfillment_id", sa.Uuid(), nullable=True),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(40), server_default="manual", nullable=False),
        sa.Column("status", sa.String(32), server_default="pending", nullable=False),
        sa.Column("provider_ref", sa.String(160), nullable=True),
        sa.Column("error_note", sa.String(1000), nullable=True),
        sa.Column(
            "manual_required",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("fulfilled_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["merch_fulfillment_id"], ["merch_fulfillments.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_item_id", name="uq_merch_pod_jobs_order_item"),
    )
    op.create_index("ix_merch_pod_jobs_host_id", "merch_pod_jobs", ["host_id"])
    op.create_index("ix_merch_pod_jobs_status", "merch_pod_jobs", ["status"])

    op.add_column(
        "host_profiles",
        sa.Column(
            "merch_storefront_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "host_profiles",
        sa.Column("merch_storefront_title", sa.String(160), nullable=True),
    )
    op.add_column(
        "host_profiles",
        sa.Column("merch_storefront_description", sa.String(500), nullable=True),
    )
    op.add_column(
        "host_profiles",
        sa.Column(
            "merch_storefront_visibility",
            sa.String(32),
            server_default="hidden",
            nullable=False,
        ),
    )


def downgrade() -> None:
    for col in (
        "merch_storefront_visibility",
        "merch_storefront_description",
        "merch_storefront_title",
        "merch_storefront_enabled",
    ):
        op.drop_column("host_profiles", col)
    op.drop_table("merch_pod_jobs")
    op.drop_table("merch_print_on_demand_integrations")
    op.drop_table("merch_revenue_splits")
    op.drop_table("merch_stock_alerts")
    op.drop_table("merch_reviews")
    op.drop_table("merch_cart_items")
    op.drop_table("merch_carts")
    op.drop_constraint("fk_merch_fulfillments_bundle_id", "merch_fulfillments", type_="foreignkey")
    op.drop_constraint(
        "fk_merch_fulfillments_shipping_address_id", "merch_fulfillments", type_="foreignkey"
    )
    for col in (
        "bundle_id",
        "pod_job_id",
        "delivered_at",
        "shipped_at",
        "carrier",
        "tracking_number",
        "shipping_address_id",
        "pickup_qr_token_hash",
        "fulfillment_method",
    ):
        op.drop_column("merch_fulfillments", col)
    op.alter_column("merch_fulfillments", "event_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_table("merch_shipping_addresses")
    op.drop_table("merch_shipping_zones")
    op.drop_constraint("fk_order_items_bundle_id", "order_items", type_="foreignkey")
    op.drop_column("order_items", "bundle_id")
    op.drop_constraint("fk_orders_merch_discount_code_id", "orders", type_="foreignkey")
    for col in (
        "fulfillment_method",
        "shipping_address_id",
        "shipping_amount",
        "merch_discount_amount",
        "merch_discount_code_snapshot",
        "merch_discount_code_id",
    ):
        op.drop_column("orders", col)
    op.drop_table("merch_discount_redemptions")
    op.drop_table("merch_discount_codes")
    op.drop_table("merch_bundles")
    op.drop_column("event_merch_variants", "print_on_demand_variant_ref")
    op.drop_column("event_merch_variants", "low_stock_threshold")
    op.drop_constraint(
        "fk_event_merch_products_sponsor_id", "event_merch_products", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_event_merch_products_required_vault_item_id",
        "event_merch_products",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_event_merch_products_size_chart_id", "event_merch_products", type_="foreignkey"
    )
    for col in (
        "low_stock_threshold",
        "size_chart_id",
        "print_on_demand_enabled",
        "shipping_enabled",
        "pickup_enabled",
        "post_event_drop_at",
        "related_fan_badge_id",
        "requires_vault_access",
        "requires_check_in",
        "sponsor_split_value",
        "sponsor_split_type",
        "sponsor_description",
        "sponsor_logo_url",
        "sponsor_brand_name",
        "sponsor_id",
        "is_sponsor_branded",
        "required_access_type",
        "required_vault_item_id",
        "is_vault_exclusive",
        "is_merch_only_enabled",
        "storefront_visibility",
        "is_event_linked",
    ):
        op.drop_column("event_merch_products", col)
    op.alter_column("event_merch_products", "event_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_table("merch_size_charts")
