"""Add soft-unpin timestamp to message_pins.

Revision ID: 20260718_0057
Revises: 20260718_0056
Create Date: 2026-07-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260718_0057"
down_revision = "20260718_0056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "message_pins",
        sa.Column("unpinned_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_message_pins_unpinned_at", "message_pins", ["unpinned_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_message_pins_unpinned_at", table_name="message_pins")
    op.drop_column("message_pins", "unpinned_at")
