"""Alembic: add notes to platform_fee_settings.

Revision ID: 20260721_0112
Revises: 20260721_0111
Create Date: 2026-07-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260721_0112"
down_revision = "20260721_0111"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "platform_fee_settings",
        sa.Column("notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("platform_fee_settings", "notes")
