"""CMS homepage browse tiles (interest / city / price / when).

Revision ID: 20260718_0037
Revises: 20260717_0036
Create Date: 2026-07-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260718_0037"
down_revision = "20260717_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cms_browse_tiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rail", sa.String(length=32), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("hint", sa.String(length=200), nullable=True),
        sa.Column("href", sa.String(length=500), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["archived_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cms_browse_tiles_rail", "cms_browse_tiles", ["rail"])
    op.create_index("ix_cms_browse_tiles_status", "cms_browse_tiles", ["status"])


def downgrade() -> None:
    op.drop_index("ix_cms_browse_tiles_status", table_name="cms_browse_tiles")
    op.drop_index("ix_cms_browse_tiles_rail", table_name="cms_browse_tiles")
    op.drop_table("cms_browse_tiles")
