"""Store domain ambassador participant/attribution on orders.

Revision ID: 20260719_0085
Revises: 20260719_0084
Create Date: 2026-07-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260719_0085"
down_revision = "20260719_0084"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("ambassador_participant_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("ambassador_attribution_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_orders_ambassador_participant_id",
        "orders",
        "ambassador_participants",
        ["ambassador_participant_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_orders_ambassador_attribution_id",
        "orders",
        "ambassador_attributions",
        ["ambassador_attribution_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_orders_ambassador_participant_id",
        "orders",
        ["ambassador_participant_id"],
    )
    op.create_index(
        "ix_orders_ambassador_attribution_id",
        "orders",
        ["ambassador_attribution_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_orders_ambassador_attribution_id", table_name="orders")
    op.drop_index("ix_orders_ambassador_participant_id", table_name="orders")
    op.drop_constraint(
        "fk_orders_ambassador_attribution_id", "orders", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_orders_ambassador_participant_id", "orders", type_="foreignkey"
    )
    op.drop_column("orders", "ambassador_attribution_id")
    op.drop_column("orders", "ambassador_participant_id")
