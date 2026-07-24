"""Create featured_placements and migrate from featured_placement_slots.

Revision ID: 20260717_0026
Revises: 20260717_0025
Create Date: 2026-07-17
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260717_0026"
down_revision: Union[str, Sequence[str], None] = "20260717_0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "featured_placements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("placement_key", sa.String(length=220), nullable=False),
        sa.Column("placement_type", sa.String(length=40), nullable=False),
        sa.Column("context_type", sa.String(length=32), nullable=False),
        sa.Column("context_id", sa.Uuid(), nullable=True),
        sa.Column("country_id", sa.Uuid(), nullable=True),
        sa.Column("state_id", sa.Uuid(), nullable=True),
        sa.Column("city_id", sa.Uuid(), nullable=True),
        sa.Column("area_id", sa.Uuid(), nullable=True),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("slot_number", sa.Integer(), nullable=False),
        sa.Column("title_override", sa.String(length=200), nullable=True),
        sa.Column("subtitle_override", sa.String(length=255), nullable=True),
        sa.Column("badge_text", sa.String(length=80), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
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
        sa.CheckConstraint(
            "slot_number IN (1, 2)", name="ck_featured_placements_slot"
        ),
        sa.CheckConstraint(
            "placement_type IN ("
            "'homepage', 'events_page', 'country_page', 'state_page', "
            "'city_page', 'category_page', 'city_category_page')",
            name="ck_featured_placements_type",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'scheduled', 'expired', 'archived')",
            name="ck_featured_placements_status",
        ),
        sa.ForeignKeyConstraint(
            ["area_id"], ["locations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["event_categories.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["city_id"], ["locations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["country_id"], ["locations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["event_id"], ["events.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["state_id"], ["locations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "placement_key",
            "slot_number",
            name="uq_featured_placements_key_slot",
        ),
    )
    op.create_index(
        "ix_featured_placements_placement_key",
        "featured_placements",
        ["placement_key"],
    )
    op.create_index(
        "ix_featured_placements_placement_type",
        "featured_placements",
        ["placement_type"],
    )
    op.create_index(
        "ix_featured_placements_context_type",
        "featured_placements",
        ["context_type"],
    )
    op.create_index(
        "ix_featured_placements_context_id",
        "featured_placements",
        ["context_id"],
    )
    op.create_index(
        "ix_featured_placements_country_id",
        "featured_placements",
        ["country_id"],
    )
    op.create_index(
        "ix_featured_placements_state_id", "featured_placements", ["state_id"]
    )
    op.create_index(
        "ix_featured_placements_city_id", "featured_placements", ["city_id"]
    )
    op.create_index(
        "ix_featured_placements_area_id", "featured_placements", ["area_id"]
    )
    op.create_index(
        "ix_featured_placements_category_id",
        "featured_placements",
        ["category_id"],
    )
    op.create_index(
        "ix_featured_placements_event_id", "featured_placements", ["event_id"]
    )
    op.create_index(
        "ix_featured_placements_status", "featured_placements", ["status"]
    )

    # Migrate legacy featured_placement_slots rows when present.
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "featured_placement_slots" in inspector.get_table_names():
        rows = conn.execute(
            sa.text(
                "SELECT id, context_key, context_type, location_id, category_id, "
                "slot_index, event_id, updated_by, created_at, updated_at "
                "FROM featured_placement_slots"
            )
        ).mappings().all()
        type_map = {
            "global_homepage": ("homepage", "global"),
            "events": ("events_page", "global"),
            "country": ("country_page", "country"),
            "state": ("state_page", "state"),
            "city": ("city_page", "city"),
            "category": ("category_page", "category"),
            "city_category": ("city_category_page", "city_category"),
            "homepage": ("homepage", "global"),
            "events_page": ("events_page", "global"),
        }
        for row in rows:
            ctx = row["context_type"]
            placement_type, context_type = type_map.get(
                ctx, ("events_page", "global")
            )
            location_id = row["location_id"]
            category_id = row["category_id"]
            country_id = state_id = city_id = None
            if placement_type == "country_page":
                country_id = location_id
            elif placement_type == "state_page":
                state_id = location_id
            elif placement_type in {"city_page", "city_category_page"}:
                city_id = location_id

            if placement_type == "homepage":
                placement_key = "homepage"
            elif placement_type == "events_page":
                placement_key = "events_page"
            elif placement_type == "country_page" and country_id:
                placement_key = f"country_page:{country_id}"
            elif placement_type == "state_page" and state_id:
                placement_key = f"state_page:{state_id}"
            elif placement_type == "city_page" and city_id:
                placement_key = f"city_page:{city_id}"
            elif placement_type == "category_page" and category_id:
                placement_key = f"category_page:{category_id}"
            elif (
                placement_type == "city_category_page"
                and city_id
                and category_id
            ):
                placement_key = f"city_category_page:{city_id}:{category_id}"
            else:
                placement_key = row["context_key"] or placement_type

            context_id = location_id or category_id
            status = "active" if row["event_id"] else "draft"
            conn.execute(
                sa.text(
                    """
                    INSERT INTO featured_placements (
                      id, placement_key, placement_type, context_type, context_id,
                      country_id, state_id, city_id, area_id, category_id,
                      event_id, slot_number, status, created_by, updated_by,
                      created_at, updated_at
                    ) VALUES (
                      :id, :placement_key, :placement_type, :context_type, :context_id,
                      :country_id, :state_id, :city_id, NULL, :category_id,
                      :event_id, :slot_number, :status, NULL, :updated_by,
                      :created_at, :updated_at
                    )
                    ON CONFLICT (placement_key, slot_number) DO NOTHING
                    """
                ),
                {
                    "id": str(row["id"] or uuid.uuid4()),
                    "placement_key": placement_key,
                    "placement_type": placement_type,
                    "context_type": context_type,
                    "context_id": str(context_id) if context_id else None,
                    "country_id": str(country_id) if country_id else None,
                    "state_id": str(state_id) if state_id else None,
                    "city_id": str(city_id) if city_id else None,
                    "category_id": str(category_id) if category_id else None,
                    "event_id": str(row["event_id"]) if row["event_id"] else None,
                    "slot_number": row["slot_index"],
                    "status": status,
                    "updated_by": (
                        str(row["updated_by"]) if row["updated_by"] else None
                    ),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                },
            )

        op.drop_table("featured_placement_slots")


def downgrade() -> None:
    op.create_table(
        "featured_placement_slots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("context_key", sa.String(length=180), nullable=False),
        sa.Column("context_type", sa.String(length=32), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=True),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("slot_index", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
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
            ["category_id"], ["event_categories.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["event_id"], ["events.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["location_id"], ["locations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "context_key",
            "slot_index",
            name="uq_featured_placement_context_slot",
        ),
    )
    op.drop_table("featured_placements")
