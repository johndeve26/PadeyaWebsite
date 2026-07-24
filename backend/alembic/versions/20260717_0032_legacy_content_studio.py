"""Legacy Content Studio tables.

Revision ID: 20260717_0032
Revises: 20260717_0031
Create Date: 2026-07-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260717_0032"
down_revision = "20260717_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

    op.create_table(
        "host_legacy_pages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("tagline", sa.String(length=280), nullable=True),
        sa.Column("primary_category_slug", sa.String(length=120), nullable=True),
        sa.Column("host_type_slug", sa.String(length=120), nullable=True),
        sa.Column("service_areas", json_type, nullable=True),
        sa.Column("sponsorship_available", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sponsorship_note", sa.Text(), nullable=True),
        sa.Column("primary_cta_label", sa.String(length=80), nullable=True),
        sa.Column("primary_cta_type", sa.String(length=40), nullable=True),
        sa.Column("primary_cta_value", sa.String(length=500), nullable=True),
        sa.Column("secondary_cta_label", sa.String(length=80), nullable=True),
        sa.Column("secondary_cta_type", sa.String(length=40), nullable=True),
        sa.Column("secondary_cta_value", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("host_id", name="uq_host_legacy_pages_host_id"),
    )
    op.create_index("ix_host_legacy_pages_host_id", "host_legacy_pages", ["host_id"])

    op.create_table(
        "host_legacy_content_blocks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("block_type", sa.String(length=64), nullable=False),
        sa.Column("title_override", sa.String(length=160), nullable=True),
        sa.Column("description_override", sa.Text(), nullable=True),
        sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("layout_style", sa.String(length=64), nullable=False, server_default="default"),
        sa.Column("source_type", sa.String(length=32), nullable=False, server_default="automatic"),
        sa.Column("item_limit", sa.Integer(), nullable=True),
        sa.Column("config", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_host_legacy_content_blocks_host_id", "host_legacy_content_blocks", ["host_id"])
    op.create_index("ix_host_legacy_content_blocks_block_type", "host_legacy_content_blocks", ["block_type"])
    op.create_index("ix_host_legacy_content_blocks_sort_order", "host_legacy_content_blocks", ["sort_order"])

    op.create_table(
        "host_legacy_featured_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("item_type", sa.String(length=40), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("placement", sa.String(length=64), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_host_legacy_featured_items_host_id", "host_legacy_featured_items", ["host_id"])
    op.create_index("ix_host_legacy_featured_items_item_type", "host_legacy_featured_items", ["item_type"])
    op.create_index("ix_host_legacy_featured_items_placement", "host_legacy_featured_items", ["placement"])

    op.create_table(
        "host_social_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("platform", sa.String(length=64), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_host_social_links_host_id", "host_social_links", ["host_id"])

    op.create_table(
        "host_contact_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("preference", sa.String(length=40), nullable=False, server_default="none"),
        sa.Column("public_email", sa.String(length=320), nullable=True),
        sa.Column("show_contact_form", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("preferred_channel", sa.String(length=64), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("host_id", name="uq_host_contact_settings_host_id"),
    )
    op.create_index("ix_host_contact_settings_host_id", "host_contact_settings", ["host_id"])


def downgrade() -> None:
    op.drop_index("ix_host_contact_settings_host_id", table_name="host_contact_settings")
    op.drop_table("host_contact_settings")
    op.drop_index("ix_host_social_links_host_id", table_name="host_social_links")
    op.drop_table("host_social_links")
    op.drop_index("ix_host_legacy_featured_items_placement", table_name="host_legacy_featured_items")
    op.drop_index("ix_host_legacy_featured_items_item_type", table_name="host_legacy_featured_items")
    op.drop_index("ix_host_legacy_featured_items_host_id", table_name="host_legacy_featured_items")
    op.drop_table("host_legacy_featured_items")
    op.drop_index("ix_host_legacy_content_blocks_sort_order", table_name="host_legacy_content_blocks")
    op.drop_index("ix_host_legacy_content_blocks_block_type", table_name="host_legacy_content_blocks")
    op.drop_index("ix_host_legacy_content_blocks_host_id", table_name="host_legacy_content_blocks")
    op.drop_table("host_legacy_content_blocks")
    op.drop_index("ix_host_legacy_pages_host_id", table_name="host_legacy_pages")
    op.drop_table("host_legacy_pages")
