"""Ambassador referral codes unique per campaign + order attribution source.

Revision ID: 20260719_0082
Revises: 20260719_0081
Create Date: 2026-07-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260719_0082"
down_revision = "20260719_0081"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("uq_ambassadors_event_referral", table_name="ambassadors")
    op.create_index(
        "uq_ambassadors_campaign_referral",
        "ambassadors",
        ["campaign_id", "referral_code"],
        unique=True,
        postgresql_where=sa.text("campaign_id IS NOT NULL"),
        sqlite_where=sa.text("campaign_id IS NOT NULL"),
    )
    op.create_index(
        "uq_ambassadors_event_referral_legacy",
        "ambassadors",
        ["event_id", "referral_code"],
        unique=True,
        postgresql_where=sa.text("event_id IS NOT NULL AND campaign_id IS NULL"),
        sqlite_where=sa.text("event_id IS NOT NULL AND campaign_id IS NULL"),
    )

    op.add_column(
        "orders",
        sa.Column(
            "referral_attribution_source",
            sa.String(length=32),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("orders", "referral_attribution_source")
    op.drop_index("uq_ambassadors_event_referral_legacy", table_name="ambassadors")
    op.drop_index("uq_ambassadors_campaign_referral", table_name="ambassadors")
    op.create_index(
        "uq_ambassadors_event_referral",
        "ambassadors",
        ["event_id", "referral_code"],
        unique=True,
        postgresql_where=sa.text("event_id IS NOT NULL"),
        sqlite_where=sa.text("event_id IS NOT NULL"),
    )
