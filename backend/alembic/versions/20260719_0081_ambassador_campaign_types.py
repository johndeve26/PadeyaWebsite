"""Ambassador campaign types: event_tickets | event_merch.

Revision ID: 20260719_0081
Revises: 20260719_0080
Create Date: 2026-07-19

- ambassador_campaigns.campaign_type
- Allow one open campaign per (event_id, campaign_type)
- Ambassadors may enroll once per campaign (not once per event)
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260719_0081"
down_revision = "20260719_0080"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ambassador_campaigns",
        sa.Column(
            "campaign_type",
            sa.String(length=32),
            nullable=False,
            server_default="event_tickets",
        ),
    )
    op.create_index(
        "ix_ambassador_campaigns_campaign_type",
        "ambassador_campaigns",
        ["campaign_type"],
    )

    # Existing rows: tickets-only vs tickets+merch → both become event_tickets;
    # hosts create a separate event_merch campaign for merch-only programs.
    op.execute(
        sa.text(
            """
            UPDATE ambassador_campaigns
            SET campaign_type = 'event_tickets',
                merch_included = false
            WHERE campaign_type = 'event_tickets'
            """
        )
    )

    op.drop_index("uq_ambassadors_event_user", table_name="ambassadors")
    op.create_index(
        "uq_ambassadors_campaign_user",
        "ambassadors",
        ["campaign_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("campaign_id IS NOT NULL AND user_id IS NOT NULL"),
        sqlite_where=sa.text("campaign_id IS NOT NULL AND user_id IS NOT NULL"),
    )
    op.create_index(
        "uq_ambassadors_event_user_legacy",
        "ambassadors",
        ["event_id", "user_id"],
        unique=True,
        postgresql_where=sa.text(
            "event_id IS NOT NULL AND user_id IS NOT NULL AND campaign_id IS NULL"
        ),
        sqlite_where=sa.text(
            "event_id IS NOT NULL AND user_id IS NOT NULL AND campaign_id IS NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_ambassadors_event_user_legacy", table_name="ambassadors")
    op.drop_index("uq_ambassadors_campaign_user", table_name="ambassadors")
    op.create_index(
        "uq_ambassadors_event_user",
        "ambassadors",
        ["event_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("event_id IS NOT NULL AND user_id IS NOT NULL"),
        sqlite_where=sa.text("event_id IS NOT NULL AND user_id IS NOT NULL"),
    )
    op.drop_index(
        "ix_ambassador_campaigns_campaign_type",
        table_name="ambassador_campaigns",
    )
    op.drop_column("ambassador_campaigns", "campaign_type")
