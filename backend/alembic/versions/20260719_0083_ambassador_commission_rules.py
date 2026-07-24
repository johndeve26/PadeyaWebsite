"""Ambassador campaign commission / reward rules.

Revision ID: 20260719_0083
Revises: 20260719_0082
Create Date: 2026-07-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260719_0083"
down_revision = "20260719_0082"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ambassador_campaigns",
        sa.Column(
            "commission_type",
            sa.String(length=32),
            nullable=False,
            server_default="percentage",
        ),
    )
    op.add_column(
        "ambassador_campaigns",
        sa.Column(
            "commission_value",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="5.00",
        ),
    )
    op.add_column(
        "ambassador_campaigns",
        sa.Column(
            "applies_to",
            sa.String(length=32),
            nullable=False,
            server_default="tickets",
        ),
    )
    op.add_column(
        "ambassador_campaigns",
        sa.Column(
            "hold_period_days",
            sa.Integer(),
            nullable=False,
            server_default="7",
        ),
    )
    op.add_column(
        "ambassador_campaigns",
        sa.Column("payout_minimum", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.add_column(
        "ambassador_campaigns",
        sa.Column(
            "max_commission_per_order",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
        ),
    )
    op.add_column(
        "ambassador_campaigns",
        sa.Column("free_ticket_after_sales", sa.Integer(), nullable=True),
    )
    op.add_column(
        "ambassador_campaigns",
        sa.Column(
            "leaderboard_reward_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "ambassador_campaigns",
        sa.Column(
            "leaderboard_reward_description",
            sa.String(length=500),
            nullable=True,
        ),
    )

    # Backfill from legacy percent + campaign_type.
    op.execute(
        sa.text(
            """
            UPDATE ambassador_campaigns
            SET commission_type = 'percentage',
                commission_value = commission_percent,
                applies_to = CASE
                    WHEN campaign_type = 'event_merch' THEN 'merch'
                    ELSE 'tickets'
                END
            """
        )
    )

    op.add_column(
        "ambassador_sales",
        sa.Column("hold_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "ambassador_sales",
        sa.Column("commission_type", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "ambassadors",
        sa.Column(
            "free_ticket_earned_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("ambassadors", "free_ticket_earned_at")
    op.drop_column("ambassador_sales", "commission_type")
    op.drop_column("ambassador_sales", "hold_until")
    op.drop_column("ambassador_campaigns", "leaderboard_reward_description")
    op.drop_column("ambassador_campaigns", "leaderboard_reward_enabled")
    op.drop_column("ambassador_campaigns", "free_ticket_after_sales")
    op.drop_column("ambassador_campaigns", "max_commission_per_order")
    op.drop_column("ambassador_campaigns", "payout_minimum")
    op.drop_column("ambassador_campaigns", "hold_period_days")
    op.drop_column("ambassador_campaigns", "applies_to")
    op.drop_column("ambassador_campaigns", "commission_value")
    op.drop_column("ambassador_campaigns", "commission_type")
