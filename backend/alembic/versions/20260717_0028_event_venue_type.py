"""Add events.venue_type for Studio location taxonomy.

Revision ID: 20260717_0028
Revises: 20260717_0027
Create Date: 2026-07-17
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260717_0028"
down_revision: Union[str, Sequence[str], None] = "20260717_0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column("venue_type", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("events", "venue_type")
