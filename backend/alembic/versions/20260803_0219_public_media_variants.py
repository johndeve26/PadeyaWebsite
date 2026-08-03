"""Create public_media_assets / variants + companion JSONB media fields.

Revision ID: 20260803_0219
Revises: 20260803_0218
Create Date: 2026-08-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260803_0219"
down_revision = "20260803_0218"
branch_labels = None
depends_on = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "public_media_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_type", sa.String(length=64), nullable=True),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("media_role", sa.String(length=64), nullable=False),
        sa.Column("source_key", sa.String(length=500), nullable=True),
        sa.Column("source_mime", sa.String(length=64), nullable=True),
        sa.Column("source_width", sa.Integer(), nullable=True),
        sa.Column("source_height", sa.Integer(), nullable=True),
        sa.Column("source_byte_size", sa.BigInteger(), nullable=True),
        sa.Column("alt_text", sa.String(length=500), nullable=True),
        sa.Column("focal_x", sa.Float(), nullable=True),
        sa.Column("focal_y", sa.Float(), nullable=True),
        sa.Column("processing_status", sa.String(length=32), nullable=False),
        sa.Column("processing_version", sa.String(length=16), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
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
        sa.Column("replaced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_public_media_assets_owner",
        "public_media_assets",
        ["owner_type", "owner_id"],
    )
    op.create_index(
        "ix_public_media_assets_role_status",
        "public_media_assets",
        ["media_role", "processing_status"],
    )
    op.create_index(
        op.f("ix_public_media_assets_media_role"),
        "public_media_assets",
        ["media_role"],
    )
    op.create_index(
        op.f("ix_public_media_assets_processing_status"),
        "public_media_assets",
        ["processing_status"],
    )
    op.create_index(
        op.f("ix_public_media_assets_deleted_at"),
        "public_media_assets",
        ["deleted_at"],
    )

    op.create_table(
        "public_media_variants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("variant_type", sa.String(length=32), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("public_url", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("quality", sa.Integer(), nullable=True),
        sa.Column("processing_version", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"], ["public_media_assets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "asset_id", "variant_type", name="uq_public_media_variants_asset_type"
        ),
    )
    op.create_index(
        "ix_public_media_variants_asset", "public_media_variants", ["asset_id"]
    )

    # Companion JSONB payloads (nullable) — url columns remain display URLs.
    op.add_column("events", sa.Column("banner_media", JSON_TYPE, nullable=True))
    op.add_column("events", sa.Column("mobile_banner_media", JSON_TYPE, nullable=True))
    op.add_column(
        "event_media", sa.Column("thumbnail_url", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "event_media", sa.Column("full_url", sa.String(length=500), nullable=True)
    )
    op.add_column("event_media", sa.Column("public_media", JSON_TYPE, nullable=True))
    op.add_column("host_profiles", sa.Column("avatar_media", JSON_TYPE, nullable=True))
    op.add_column("host_profiles", sa.Column("cover_media", JSON_TYPE, nullable=True))
    op.add_column("fan_passports", sa.Column("avatar_media", JSON_TYPE, nullable=True))
    op.add_column(
        "event_merch_products", sa.Column("image_media", JSON_TYPE, nullable=True)
    )
    op.add_column("blog_posts", sa.Column("cover_media", JSON_TYPE, nullable=True))


def downgrade() -> None:
    op.drop_column("blog_posts", "cover_media")
    op.drop_column("event_merch_products", "image_media")
    op.drop_column("fan_passports", "avatar_media")
    op.drop_column("host_profiles", "cover_media")
    op.drop_column("host_profiles", "avatar_media")
    op.drop_column("event_media", "public_media")
    op.drop_column("event_media", "full_url")
    op.drop_column("event_media", "thumbnail_url")
    op.drop_column("events", "mobile_banner_media")
    op.drop_column("events", "banner_media")
    op.drop_table("public_media_variants")
    op.drop_table("public_media_assets")
