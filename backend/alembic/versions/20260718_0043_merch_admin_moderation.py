"""Merch admin moderation fields and product reports.

Revision ID: 20260718_0043
Revises: 20260718_0042
Create Date: 2026-07-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260718_0043"
down_revision = "20260718_0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "event_merch_products",
        sa.Column(
            "moderation_status",
            sa.String(length=32),
            server_default="clear",
            nullable=False,
        ),
    )
    op.add_column(
        "event_merch_products",
        sa.Column("moderation_note", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "event_merch_products",
        sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "event_merch_products",
        sa.Column("moderated_by_user_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_event_merch_products_moderated_by",
        "event_merch_products",
        "users",
        ["moderated_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_event_merch_products_moderation_status",
        "event_merch_products",
        ["moderation_status"],
    )

    op.create_table(
        "merch_product_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("reporter_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="open", nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("resolution_note", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["product_id"], ["event_merch_products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_merch_product_reports_product_id", "merch_product_reports", ["product_id"]
    )
    op.create_index(
        "ix_merch_product_reports_status", "merch_product_reports", ["status"]
    )


def downgrade() -> None:
    op.drop_table("merch_product_reports")
    op.drop_index(
        "ix_event_merch_products_moderation_status", table_name="event_merch_products"
    )
    op.drop_constraint(
        "fk_event_merch_products_moderated_by",
        "event_merch_products",
        type_="foreignkey",
    )
    op.drop_column("event_merch_products", "moderated_by_user_id")
    op.drop_column("event_merch_products", "moderated_at")
    op.drop_column("event_merch_products", "moderation_note")
    op.drop_column("event_merch_products", "moderation_status")
