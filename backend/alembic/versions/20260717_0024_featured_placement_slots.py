"""Featured placement slots for Pàdéyá Picks.

Revision ID: 20260717_0024
Revises: 20260717_0023
Create Date: 2026-07-17
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260717_0024"
down_revision: Union[str, Sequence[str], None] = "20260717_0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "featured_placement_slots",
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.CheckConstraint("slot_index IN (1, 2)", name="ck_featured_placement_slot_index"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slot_index", name="uq_featured_placement_slot_index"),
    )
    op.create_index(
        "ix_featured_placement_slots_event_id",
        "featured_placement_slots",
        ["event_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_featured_placement_slots_event_id", table_name="featured_placement_slots")
    op.drop_table("featured_placement_slots")
