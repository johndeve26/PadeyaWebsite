"""Taxonomy vocabulary, locations, links, and content graph.

Revision ID: 20260717_0023
Revises: 20260717_0022
Create Date: 2026-07-17
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260717_0023"
down_revision: Union[str, Sequence[str], None] = "20260717_0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _vocab_table(name: str) -> None:
    op.create_table(
        name,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=140), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("featured", sa.Boolean(), nullable=False),
        sa.Column("seo_title", sa.String(length=200), nullable=True),
        sa.Column("seo_description", sa.String(length=320), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(f"ix_{name}_slug", name, ["slug"])


def upgrade() -> None:
    _vocab_table("taxonomy_categories")
    _vocab_table("taxonomy_tags")
    _vocab_table("taxonomy_vibes")
    _vocab_table("taxonomy_audience_types")
    _vocab_table("host_types")
    _vocab_table("venue_types")

    op.create_table(
        "taxonomy_subcategories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=140), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("featured", sa.Boolean(), nullable=False),
        sa.Column("seo_title", sa.String(length=200), nullable=True),
        sa.Column("seo_description", sa.String(length=320), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["category_id"], ["taxonomy_categories.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "category_id", "slug", name="uq_taxonomy_subcategories_cat_slug"
        ),
    )
    op.create_index(
        "ix_taxonomy_subcategories_category_id",
        "taxonomy_subcategories",
        ["category_id"],
    )
    op.create_index(
        "ix_taxonomy_subcategories_slug", "taxonomy_subcategories", ["slug"]
    )

    op.create_table(
        "locations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("state_code", sa.String(length=16), nullable=True),
        sa.Column("country_code", sa.String(length=8), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
        sa.ForeignKeyConstraint(["parent_id"], ["locations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_locations_kind", "locations", ["kind"])
    op.create_index("ix_locations_slug", "locations", ["slug"])
    op.create_index("ix_locations_parent_id", "locations", ["parent_id"])
    op.create_index("ix_locations_kind_slug", "locations", ["kind", "slug"])

    op.create_table(
        "event_taxonomy_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("link_type", sa.String(length=48), nullable=False),
        sa.Column("taxonomy_id", sa.Uuid(), nullable=False),
        sa.Column("taxonomy_slug", sa.String(length=140), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_id",
            "link_type",
            "taxonomy_id",
            name="uq_event_taxonomy_links_event_type_id",
        ),
    )
    op.create_index(
        "ix_event_taxonomy_links_event_id", "event_taxonomy_links", ["event_id"]
    )
    op.create_index(
        "ix_event_taxonomy_links_link_type", "event_taxonomy_links", ["link_type"]
    )
    op.create_index(
        "ix_event_taxonomy_links_taxonomy_slug",
        "event_taxonomy_links",
        ["taxonomy_slug"],
    )
    op.create_index(
        "ix_event_taxonomy_links_type_slug",
        "event_taxonomy_links",
        ["link_type", "taxonomy_slug"],
    )

    op.create_table(
        "host_taxonomy_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("link_type", sa.String(length=48), nullable=False),
        sa.Column("taxonomy_id", sa.Uuid(), nullable=False),
        sa.Column("taxonomy_slug", sa.String(length=140), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "host_id",
            "link_type",
            "taxonomy_id",
            name="uq_host_taxonomy_links_host_type_id",
        ),
    )
    op.create_index(
        "ix_host_taxonomy_links_host_id", "host_taxonomy_links", ["host_id"]
    )
    op.create_index(
        "ix_host_taxonomy_links_link_type", "host_taxonomy_links", ["link_type"]
    )
    op.create_index(
        "ix_host_taxonomy_links_taxonomy_slug",
        "host_taxonomy_links",
        ["taxonomy_slug"],
    )
    op.create_index(
        "ix_host_taxonomy_links_type_slug",
        "host_taxonomy_links",
        ["link_type", "taxonomy_slug"],
    )

    op.create_table(
        "host_location_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "host_id", "location_id", name="uq_host_location_links_host_loc"
        ),
    )
    op.create_index(
        "ix_host_location_links_host_id", "host_location_links", ["host_id"]
    )
    op.create_index(
        "ix_host_location_links_location_id", "host_location_links", ["location_id"]
    )

    op.create_table(
        "content_relationships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=48), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("target_type", sa.String(length=48), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", sa.String(length=64), nullable=False),
        sa.Column("weight", sa.Numeric(8, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=False),
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
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_type",
            "source_id",
            "target_type",
            "target_id",
            "relationship_type",
            name="uq_content_relationships_edge",
        ),
    )
    op.create_index(
        "ix_content_relationships_source",
        "content_relationships",
        ["source_type", "source_id", "relationship_type"],
    )
    op.create_index(
        "ix_content_relationships_target",
        "content_relationships",
        ["target_type", "target_id"],
    )

    op.add_column(
        "events",
        sa.Column("primary_category_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "events",
        sa.Column("location_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_events_primary_category_id_taxonomy_categories",
        "events",
        "taxonomy_categories",
        ["primary_category_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_events_location_id_locations",
        "events",
        "locations",
        ["location_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_events_primary_category_id", "events", ["primary_category_id"]
    )
    op.create_index("ix_events_location_id", "events", ["location_id"])
    op.create_index(
        "ix_events_primary_category_start",
        "events",
        ["primary_category_id", "start_datetime"],
    )
    op.create_index(
        "ix_events_location_start",
        "events",
        ["location_id", "start_datetime"],
    )


def downgrade() -> None:
    op.drop_index("ix_events_location_start", table_name="events")
    op.drop_index("ix_events_primary_category_start", table_name="events")
    op.drop_index("ix_events_location_id", table_name="events")
    op.drop_index("ix_events_primary_category_id", table_name="events")
    op.drop_constraint(
        "fk_events_location_id_locations", "events", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_events_primary_category_id_taxonomy_categories",
        "events",
        type_="foreignkey",
    )
    op.drop_column("events", "location_id")
    op.drop_column("events", "primary_category_id")

    op.drop_index("ix_content_relationships_target", table_name="content_relationships")
    op.drop_index("ix_content_relationships_source", table_name="content_relationships")
    op.drop_table("content_relationships")

    op.drop_index("ix_host_location_links_location_id", table_name="host_location_links")
    op.drop_index("ix_host_location_links_host_id", table_name="host_location_links")
    op.drop_table("host_location_links")

    op.drop_index("ix_host_taxonomy_links_type_slug", table_name="host_taxonomy_links")
    op.drop_index(
        "ix_host_taxonomy_links_taxonomy_slug", table_name="host_taxonomy_links"
    )
    op.drop_index("ix_host_taxonomy_links_link_type", table_name="host_taxonomy_links")
    op.drop_index("ix_host_taxonomy_links_host_id", table_name="host_taxonomy_links")
    op.drop_table("host_taxonomy_links")

    op.drop_index(
        "ix_event_taxonomy_links_type_slug", table_name="event_taxonomy_links"
    )
    op.drop_index(
        "ix_event_taxonomy_links_taxonomy_slug", table_name="event_taxonomy_links"
    )
    op.drop_index("ix_event_taxonomy_links_link_type", table_name="event_taxonomy_links")
    op.drop_index("ix_event_taxonomy_links_event_id", table_name="event_taxonomy_links")
    op.drop_table("event_taxonomy_links")

    op.drop_index("ix_locations_kind_slug", table_name="locations")
    op.drop_index("ix_locations_parent_id", table_name="locations")
    op.drop_index("ix_locations_slug", table_name="locations")
    op.drop_index("ix_locations_kind", table_name="locations")
    op.drop_table("locations")

    op.drop_index("ix_taxonomy_subcategories_slug", table_name="taxonomy_subcategories")
    op.drop_index(
        "ix_taxonomy_subcategories_category_id", table_name="taxonomy_subcategories"
    )
    op.drop_table("taxonomy_subcategories")

    for name in (
        "venue_types",
        "host_types",
        "taxonomy_audience_types",
        "taxonomy_vibes",
        "taxonomy_tags",
        "taxonomy_categories",
    ):
        op.drop_index(f"ix_{name}_slug", table_name=name)
        op.drop_table(name)
