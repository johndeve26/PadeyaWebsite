"""Context-scoped Featured Placement Slots for Pàdéyá Picks.

Revision ID: 20260717_0025
Revises: 20260717_0024
Create Date: 2026-07-17
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260717_0025"
down_revision: Union[str, Sequence[str], None] = "20260717_0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "featured_placement_slots",
        sa.Column(
            "context_key",
            sa.String(length=180),
            nullable=False,
            server_default="events",
        ),
    )
    op.add_column(
        "featured_placement_slots",
        sa.Column(
            "context_type",
            sa.String(length=32),
            nullable=False,
            server_default="events",
        ),
    )
    op.add_column(
        "featured_placement_slots",
        sa.Column("location_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "featured_placement_slots",
        sa.Column("category_id", sa.Uuid(), nullable=True),
    )

    op.drop_constraint(
        "uq_featured_placement_slot_index",
        "featured_placement_slots",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_featured_placement_context_slot",
        "featured_placement_slots",
        ["context_key", "slot_index"],
    )
    op.create_index(
        "ix_featured_placement_slots_context_key",
        "featured_placement_slots",
        ["context_key"],
    )
    op.create_index(
        "ix_featured_placement_slots_context_type",
        "featured_placement_slots",
        ["context_type"],
    )
    op.create_index(
        "ix_featured_placement_slots_location_id",
        "featured_placement_slots",
        ["location_id"],
    )
    op.create_index(
        "ix_featured_placement_slots_category_id",
        "featured_placement_slots",
        ["category_id"],
    )
    op.create_foreign_key(
        "fk_featured_placement_slots_location_id",
        "featured_placement_slots",
        "locations",
        ["location_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_featured_placement_slots_category_id",
        "featured_placement_slots",
        "event_categories",
        ["category_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Seed empty homepage slots (events rows already migrated via server_default).
    import uuid as _uuid

    conn = op.get_bind()
    for idx in (1, 2):
        exists = conn.execute(
            sa.text(
                "SELECT 1 FROM featured_placement_slots "
                "WHERE context_key = 'global_homepage' AND slot_index = :idx"
            ),
            {"idx": idx},
        ).first()
        if exists:
            continue
        conn.execute(
            sa.text(
                "INSERT INTO featured_placement_slots "
                "(id, context_key, context_type, slot_index, event_id) "
                "VALUES (:id, 'global_homepage', 'global_homepage', :idx, NULL)"
            ),
            {"id": str(_uuid.uuid4()), "idx": idx},
        )

    op.alter_column(
        "featured_placement_slots",
        "context_key",
        server_default=None,
    )
    op.alter_column(
        "featured_placement_slots",
        "context_type",
        server_default=None,
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM featured_placement_slots WHERE context_key <> 'events'"
        )
    )
    op.drop_constraint(
        "fk_featured_placement_slots_category_id",
        "featured_placement_slots",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_featured_placement_slots_location_id",
        "featured_placement_slots",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_featured_placement_slots_category_id",
        table_name="featured_placement_slots",
    )
    op.drop_index(
        "ix_featured_placement_slots_location_id",
        table_name="featured_placement_slots",
    )
    op.drop_index(
        "ix_featured_placement_slots_context_type",
        table_name="featured_placement_slots",
    )
    op.drop_index(
        "ix_featured_placement_slots_context_key",
        table_name="featured_placement_slots",
    )
    op.drop_constraint(
        "uq_featured_placement_context_slot",
        "featured_placement_slots",
        type_="unique",
    )
    op.drop_column("featured_placement_slots", "category_id")
    op.drop_column("featured_placement_slots", "location_id")
    op.drop_column("featured_placement_slots", "context_type")
    op.drop_column("featured_placement_slots", "context_key")
    op.create_unique_constraint(
        "uq_featured_placement_slot_index",
        "featured_placement_slots",
        ["slot_index"],
    )
