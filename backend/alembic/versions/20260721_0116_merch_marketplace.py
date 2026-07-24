"""Alembic: merch marketplace discovery fields and categories.

Revision ID: 20260721_0116
Revises: 20260721_0115
Create Date: 2026-07-21

Extends event_merch_products for cross-host marketplace discovery,
host-scoped standalone slug uniqueness, category catalog, and
nullable order/fulfillment event_id for host-shop (standalone) checkout.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260721_0116"
down_revision = "20260721_0115"
branch_labels = None
depends_on = None

_CATEGORIES = [
    ("apparel", "Apparel", 10),
    ("wristbands", "Wristbands", 20),
    ("caps", "Caps", 30),
    ("masks", "Masks", 40),
    ("posters", "Posters", 50),
    ("digital", "Digital items", 60),
    ("bundles", "Bundles", 70),
    ("collectibles", "Collectibles", 80),
    ("food_drink", "Food/drink vouchers", 90),
    ("other", "Other", 100),
]


def upgrade() -> None:
    op.create_table(
        "merch_categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_merch_categories_slug"),
    )
    op.create_index("ix_merch_categories_status", "merch_categories", ["status"])

    op.add_column(
        "event_merch_products",
        sa.Column("category", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "event_merch_products",
        sa.Column(
            "tags",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
    )
    op.add_column(
        "event_merch_products",
        sa.Column("marketplace_kind", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "event_merch_products",
        sa.Column(
            "marketplace_listed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.create_index(
        "ix_event_merch_products_category",
        "event_merch_products",
        ["category"],
    )
    op.create_index(
        "ix_event_merch_products_marketplace_kind",
        "event_merch_products",
        ["marketplace_kind"],
    )
    op.create_index(
        "ix_event_merch_products_marketplace_listed",
        "event_merch_products",
        ["marketplace_listed"],
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_event_merch_products_host_slug_standalone
        ON event_merch_products (host_id, slug)
        WHERE event_id IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_event_merch_products_marketplace_discovery
        ON event_merch_products (status, moderation_status, marketplace_listed, storefront_visibility)
        """
    )

    # Backfill marketplace_kind from existing flags.
    op.execute(
        """
        UPDATE event_merch_products
        SET marketplace_kind = CASE
            WHEN storefront_visibility = 'vault_exclusive' OR is_vault_exclusive IS TRUE
                THEN 'vault_exclusive'
            WHEN storefront_visibility = 'post_event_drop'
                THEN 'post_event_drop'
            WHEN is_event_linked IS FALSE OR event_id IS NULL
                THEN 'standalone'
            WHEN requires_ticket IS TRUE
                THEN 'event_addon'
            ELSE 'event_merch'
        END
        WHERE marketplace_kind IS NULL
        """
    )

    conn = op.get_bind()
    for slug, name, sort_order in _CATEGORIES:
        conn.execute(
            sa.text(
                """
                INSERT INTO merch_categories (id, slug, name, sort_order, status)
                VALUES (gen_random_uuid(), :slug, :name, :sort_order, 'active')
                ON CONFLICT (slug) DO NOTHING
                """
            ),
            {"slug": slug, "name": name, "sort_order": sort_order},
        )

    # Host-scoped standalone checkout: orders may omit event_id; host_id required then.
    op.add_column(
        "orders",
        sa.Column("host_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_orders_host_id_hosts",
        "orders",
        "hosts",
        ["host_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_orders_host_id", "orders", ["host_id"])
    op.execute(
        """
        UPDATE orders o
        SET host_id = e.host_id
        FROM events e
        WHERE o.event_id = e.id AND o.host_id IS NULL
        """
    )
    op.alter_column("orders", "event_id", existing_type=sa.Uuid(), nullable=True)

    op.alter_column(
        "merch_fulfillments",
        "event_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "merch_fulfillments",
        "event_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    # Restore event_id NOT NULL only where present — orphan host-only orders block downgrade.
    op.execute("DELETE FROM orders WHERE event_id IS NULL")
    op.alter_column("orders", "event_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_constraint("fk_orders_host_id_hosts", "orders", type_="foreignkey")
    op.drop_index("ix_orders_host_id", table_name="orders")
    op.drop_column("orders", "host_id")

    op.execute("DROP INDEX IF EXISTS ix_event_merch_products_marketplace_discovery")
    op.execute("DROP INDEX IF EXISTS uq_event_merch_products_host_slug_standalone")
    op.drop_index("ix_event_merch_products_marketplace_listed", table_name="event_merch_products")
    op.drop_index("ix_event_merch_products_marketplace_kind", table_name="event_merch_products")
    op.drop_index("ix_event_merch_products_category", table_name="event_merch_products")
    op.drop_column("event_merch_products", "marketplace_listed")
    op.drop_column("event_merch_products", "marketplace_kind")
    op.drop_column("event_merch_products", "tags")
    op.drop_column("event_merch_products", "category")

    op.drop_index("ix_merch_categories_status", table_name="merch_categories")
    op.drop_table("merch_categories")
