"""Add related_merch_order_item_id on message threads.

Revision ID: 20260718_0046
Revises: 20260718_0045
Create Date: 2026-07-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260718_0046"
down_revision = "20260718_0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "message_threads",
        sa.Column("related_merch_order_item_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_message_threads_related_merch_order_item_id",
        "message_threads",
        "order_items",
        ["related_merch_order_item_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_message_threads_related_merch_order_item_id",
        "message_threads",
        ["related_merch_order_item_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_message_threads_related_merch_order_item_id",
        table_name="message_threads",
    )
    op.drop_constraint(
        "fk_message_threads_related_merch_order_item_id",
        "message_threads",
        type_="foreignkey",
    )
    op.drop_column("message_threads", "related_merch_order_item_id")
