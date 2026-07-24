"""Sponsor saved hosts, events, and opportunities

Revision ID: 20260723_0135
Revises: 20260723_0134
Create Date: 2026-07-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260723_0135"
down_revision: Union[str, Sequence[str], None] = "20260723_0134"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sponsor_saved_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sponsor_id", sa.Uuid(), nullable=False),
        sa.Column("saved_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("item_type", sa.String(length=32), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["sponsor_id"], ["sponsors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["saved_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "sponsor_id",
            "item_type",
            "item_id",
            name="uq_sponsor_saved_items_sponsor_type_item",
        ),
    )
    op.create_index(
        "ix_sponsor_saved_items_sponsor_id", "sponsor_saved_items", ["sponsor_id"]
    )
    op.create_index(
        "ix_sponsor_saved_items_item_type", "sponsor_saved_items", ["item_type"]
    )


def downgrade() -> None:
    op.drop_table("sponsor_saved_items")
