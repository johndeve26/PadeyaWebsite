"""Alembic: event google_place_id + formatted_address for Places venue capture."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260720_0105"
down_revision = "20260720_0104"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column("google_place_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "events",
        sa.Column("formatted_address", sa.String(length=500), nullable=True),
    )
    op.create_index("ix_events_google_place_id", "events", ["google_place_id"])


def downgrade() -> None:
    op.drop_index("ix_events_google_place_id", table_name="events")
    op.drop_column("events", "formatted_address")
    op.drop_column("events", "google_place_id")
