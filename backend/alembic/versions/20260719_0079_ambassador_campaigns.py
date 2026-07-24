"""Ambassador campaigns for host-managed open promotion.

Revision ID: 20260719_0079
Revises: 20260719_0078
Create Date: 2026-07-19

- ambassador_campaigns table
- ambassadors.campaign_id
- backfill public_open campaigns from events.open_ambassadors_enabled
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260719_0079"
down_revision = "20260719_0078"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ambassador_campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "commission_percent",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
        ),
        sa.Column("merch_included", sa.Boolean(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ambassador_campaigns_host_id", "ambassador_campaigns", ["host_id"]
    )
    op.create_index(
        "ix_ambassador_campaigns_event_id", "ambassador_campaigns", ["event_id"]
    )
    op.create_index(
        "ix_ambassador_campaigns_status", "ambassador_campaigns", ["status"]
    )

    op.add_column(
        "ambassadors",
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_ambassadors_campaign_id",
        "ambassadors",
        "ambassador_campaigns",
        ["campaign_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_ambassadors_campaign_id", "ambassadors", ["campaign_id"])

    # Backfill one public_open campaign per enabled event (portable UUIDs).
    conn = op.get_bind()
    events = conn.execute(
        sa.text(
            """
            SELECT id, host_id, open_ambassador_commission_percent
            FROM events
            WHERE open_ambassadors_enabled = true
            """
        )
    ).fetchall()
    import uuid
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    for row in events:
        conn.execute(
            sa.text(
                """
                INSERT INTO ambassador_campaigns (
                    id, host_id, event_id, name, status, commission_percent,
                    merch_included, starts_at, ends_at, created_at, updated_at
                ) VALUES (
                    :id, :host_id, :event_id, :name, :status, :commission,
                    :merch, NULL, NULL, :now, :now
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "host_id": str(row[1]),
                "event_id": str(row[0]),
                "name": "Event Ambassadors",
                "status": "public_open",
                "commission": row[2] if row[2] is not None else 5.00,
                "merch": True,
                "now": now,
            },
        )


def downgrade() -> None:
    op.drop_index("ix_ambassadors_campaign_id", table_name="ambassadors")
    op.drop_constraint("fk_ambassadors_campaign_id", "ambassadors", type_="foreignkey")
    op.drop_column("ambassadors", "campaign_id")
    op.drop_index("ix_ambassador_campaigns_status", table_name="ambassador_campaigns")
    op.drop_index("ix_ambassador_campaigns_event_id", table_name="ambassador_campaigns")
    op.drop_index("ix_ambassador_campaigns_host_id", table_name="ambassador_campaigns")
    op.drop_table("ambassador_campaigns")
