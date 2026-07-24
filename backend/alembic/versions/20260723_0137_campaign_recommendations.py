"""Sponsor campaign recommendation feedback and dismissals

Revision ID: 20260723_0137
Revises: 20260723_0136
Create Date: 2026-07-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260723_0137"
down_revision: Union[str, Sequence[str], None] = "20260723_0136"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "campaign_recommendation_dismissals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("item_type", sa.String(length=32), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column(
            "dismissed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["sponsor_campaigns.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id",
            "item_type",
            "item_id",
            name="uq_campaign_rec_dismissals_campaign_item",
        ),
    )
    op.create_index(
        "ix_campaign_rec_dismissals_campaign_id",
        "campaign_recommendation_dismissals",
        ["campaign_id"],
    )

    op.create_table(
        "campaign_recommendation_feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("sponsor_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("item_type", sa.String(length=32), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["sponsor_campaigns.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["sponsor_id"], ["sponsors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_campaign_rec_feedback_campaign_created",
        "campaign_recommendation_feedback",
        ["campaign_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("campaign_recommendation_feedback")
    op.drop_table("campaign_recommendation_dismissals")
