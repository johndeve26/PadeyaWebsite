"""Structured map/location fields on events.

Revision ID: 20260717_0031
Revises: 20260717_0030
Create Date: 2026-07-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260717_0031"
down_revision = "20260717_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("events", sa.Column("country", sa.String(length=120), nullable=True))
    op.add_column("events", sa.Column("area", sa.String(length=120), nullable=True))
    op.add_column("events", sa.Column("postcode", sa.String(length=32), nullable=True))
    op.add_column("events", sa.Column("latitude", sa.String(length=32), nullable=True))
    op.add_column("events", sa.Column("longitude", sa.String(length=32), nullable=True))
    op.add_column(
        "events",
        sa.Column("google_maps_share_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "events",
        sa.Column("google_maps_place_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "events",
        sa.Column("approximate_latitude", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "events",
        sa.Column("approximate_longitude", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "events",
        sa.Column("approximate_map_label", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("events", "approximate_map_label")
    op.drop_column("events", "approximate_longitude")
    op.drop_column("events", "approximate_latitude")
    op.drop_column("events", "google_maps_place_url")
    op.drop_column("events", "google_maps_share_url")
    op.drop_column("events", "longitude")
    op.drop_column("events", "latitude")
    op.drop_column("events", "postcode")
    op.drop_column("events", "area")
    op.drop_column("events", "country")
