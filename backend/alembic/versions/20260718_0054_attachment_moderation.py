"""Add reviewed_at for attachment moderation.

Revision ID: 20260718_0054
Revises: 20260718_0053
Create Date: 2026-07-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260718_0054"
down_revision = "20260718_0053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "message_attachments",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("message_attachments", "reviewed_at")
