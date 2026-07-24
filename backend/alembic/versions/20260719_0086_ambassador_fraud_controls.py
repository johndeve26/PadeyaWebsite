"""Ambassador fraud controls: host-owner flag, UA hash, fraud flags.

Revision ID: 20260719_0086
Revises: 20260719_0085
Create Date: 2026-07-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260719_0086"
down_revision = "20260719_0085"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ambassador_campaigns",
        sa.Column(
            "allow_host_owner_commission",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "promo_clicks",
        sa.Column("user_agent_hash", sa.String(length=64), nullable=True),
    )
    op.create_table(
        "ambassador_fraud_flags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("flag_type", sa.String(length=64), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("participant_id", sa.Uuid(), nullable=True),
        sa.Column("ip_hash", sa.String(length=128), nullable=True),
        sa.Column("click_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column(
            "details",
            sa.JSON()
            .with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["ambassador_campaigns.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["participant_id"],
            ["ambassador_participants.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ambassador_fraud_flags_flag_type",
        "ambassador_fraud_flags",
        ["flag_type"],
    )
    op.create_index(
        "ix_ambassador_fraud_flags_campaign_id",
        "ambassador_fraud_flags",
        ["campaign_id"],
    )
    op.create_index(
        "ix_ambassador_fraud_flags_participant_id",
        "ambassador_fraud_flags",
        ["participant_id"],
    )
    op.create_index(
        "ix_ambassador_fraud_flags_ip_hash",
        "ambassador_fraud_flags",
        ["ip_hash"],
    )
    op.create_index(
        "ix_ambassador_fraud_flags_status",
        "ambassador_fraud_flags",
        ["status"],
    )
    op.create_index(
        "ix_ambassador_fraud_flags_created_at",
        "ambassador_fraud_flags",
        ["created_at"],
    )
    op.create_index(
        "ix_ambassador_fraud_flags_open",
        "ambassador_fraud_flags",
        ["status", "flag_type", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_ambassador_fraud_flags_open", table_name="ambassador_fraud_flags")
    op.drop_index(
        "ix_ambassador_fraud_flags_created_at", table_name="ambassador_fraud_flags"
    )
    op.drop_index("ix_ambassador_fraud_flags_status", table_name="ambassador_fraud_flags")
    op.drop_index("ix_ambassador_fraud_flags_ip_hash", table_name="ambassador_fraud_flags")
    op.drop_index(
        "ix_ambassador_fraud_flags_participant_id", table_name="ambassador_fraud_flags"
    )
    op.drop_index(
        "ix_ambassador_fraud_flags_campaign_id", table_name="ambassador_fraud_flags"
    )
    op.drop_index(
        "ix_ambassador_fraud_flags_flag_type", table_name="ambassador_fraud_flags"
    )
    op.drop_table("ambassador_fraud_flags")
    op.drop_column("promo_clicks", "user_agent_hash")
    op.drop_column("ambassador_campaigns", "allow_host_owner_commission")
