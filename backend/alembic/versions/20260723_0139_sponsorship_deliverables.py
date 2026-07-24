"""Sponsorship deliverables fulfillment tracking

Revision ID: 20260723_0139
Revises: 20260723_0138
Create Date: 2026-07-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260723_0139"
down_revision: Union[str, Sequence[str], None] = "20260723_0138"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sponsorship_deliverables",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("deal_id", sa.Uuid(), nullable=False),
        sa.Column("placement_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("deliverable_type", sa.String(length=64), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("proof_url", sa.String(length=500), nullable=True),
        sa.Column("proof_notes", sa.Text(), nullable=True),
        sa.Column("submitted_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["deal_id"], ["sponsorship_deals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["placement_id"], ["sponsorship_placements.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sponsorship_deliverables_deal_id",
        "sponsorship_deliverables",
        ["deal_id"],
    )
    op.create_index(
        "ix_sponsorship_deliverables_status",
        "sponsorship_deliverables",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_sponsorship_deliverables_status", table_name="sponsorship_deliverables")
    op.drop_index("ix_sponsorship_deliverables_deal_id", table_name="sponsorship_deliverables")
    op.drop_table("sponsorship_deliverables")
