"""Sponsor campaigns and campaign saved items

Revision ID: 20260723_0136
Revises: 20260723_0135
Create Date: 2026-07-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260723_0136"
down_revision: Union[str, Sequence[str], None] = "20260723_0135"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sponsor_campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sponsor_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("public_ref", sa.String(length=180), nullable=False),
        sa.Column("objective", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_categories", sa.JSON(), nullable=True),
        sa.Column("target_locations", sa.JSON(), nullable=True),
        sa.Column("target_audience", sa.JSON(), nullable=True),
        sa.Column("budget_min", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("budget_max", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=8), server_default="NGN", nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("visibility", sa.String(length=32), server_default="private", nullable=False),
        sa.Column(
            "moderation_status",
            sa.String(length=32),
            server_default="not_required",
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(["sponsor_id"], ["sponsors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "sponsor_id",
            "public_ref",
            name="uq_sponsor_campaigns_sponsor_public_ref",
        ),
    )
    op.create_index(
        "ix_sponsor_campaigns_sponsor_id", "sponsor_campaigns", ["sponsor_id"]
    )
    op.create_index("ix_sponsor_campaigns_status", "sponsor_campaigns", ["status"])
    op.create_index(
        "ix_sponsor_campaigns_moderation_status",
        "sponsor_campaigns",
        ["moderation_status"],
    )

    op.create_table(
        "campaign_saved_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("sponsor_saved_item_id", sa.Uuid(), nullable=False),
        sa.Column("added_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["sponsor_campaigns.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["sponsor_saved_item_id"], ["sponsor_saved_items.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["added_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id",
            "sponsor_saved_item_id",
            name="uq_campaign_saved_items_campaign_saved",
        ),
    )
    op.create_index(
        "ix_campaign_saved_items_campaign_id", "campaign_saved_items", ["campaign_id"]
    )

    op.add_column(
        "sponsorship_inquiries",
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_sponsorship_inquiries_campaign_id",
        "sponsorship_inquiries",
        "sponsor_campaigns",
        ["campaign_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_sponsorship_inquiries_campaign_id",
        "sponsorship_inquiries",
        ["campaign_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_sponsorship_inquiries_campaign_id", "sponsorship_inquiries")
    op.drop_constraint(
        "fk_sponsorship_inquiries_campaign_id", "sponsorship_inquiries", type_="foreignkey"
    )
    op.drop_column("sponsorship_inquiries", "campaign_id")
    op.drop_table("campaign_saved_items")
    op.drop_table("sponsor_campaigns")
