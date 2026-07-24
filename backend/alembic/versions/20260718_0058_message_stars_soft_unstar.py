"""Rename message_stars.created_at to starred_at; add unstarred_at.

Revision ID: 20260718_0058
Revises: 20260718_0057
Create Date: 2026-07-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260718_0058"
down_revision = "20260718_0057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "message_stars",
        "created_at",
        new_column_name="starred_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
    )
    op.add_column(
        "message_stars",
        sa.Column("unstarred_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_message_stars_unstarred_at", "message_stars", ["unstarred_at"]
    )
    op.create_index(
        "ix_message_stars_starred_at", "message_stars", ["starred_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_message_stars_starred_at", table_name="message_stars")
    op.drop_index("ix_message_stars_unstarred_at", table_name="message_stars")
    op.drop_column("message_stars", "unstarred_at")
    op.alter_column(
        "message_stars",
        "starred_at",
        new_column_name="created_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
    )
