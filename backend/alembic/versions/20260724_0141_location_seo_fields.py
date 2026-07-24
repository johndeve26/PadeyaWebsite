"""Location SEO fields for hub metadata and indexability overrides.

Revision ID: 20260724_0141
Revises: 20260724_0140
Create Date: 2026-07-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260724_0141"
down_revision = "20260724_0140"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "locations",
        sa.Column("seo_title", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "locations",
        sa.Column("seo_description", sa.String(length=320), nullable=True),
    )
    op.add_column(
        "locations",
        sa.Column("intro_content", sa.Text(), nullable=True),
    )
    op.add_column(
        "locations",
        sa.Column(
            "seo_index_mode",
            sa.String(length=24),
            nullable=False,
            server_default="auto",
        ),
    )


def downgrade() -> None:
    op.drop_column("locations", "seo_index_mode")
    op.drop_column("locations", "intro_content")
    op.drop_column("locations", "seo_description")
    op.drop_column("locations", "seo_title")
