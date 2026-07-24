"""Admin Ambassadors: platform settings, campaign source, sale reversal.

Revision ID: 20260719_0080
Revises: 20260719_0079
Create Date: 2026-07-19

- ambassador_platform_settings (global enable/disable)
- ambassador_campaigns.source + created_by_user_id
- ambassador_sales reverse + reward status metadata
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260719_0080"
down_revision = "20260719_0079"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ambassador_platform_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "updated_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        sa.text(
            "INSERT INTO ambassador_platform_settings (id, enabled) VALUES (1, true)"
        )
    )

    op.add_column(
        "ambassador_campaigns",
        sa.Column(
            "source",
            sa.String(length=32),
            nullable=False,
            server_default="host",
        ),
    )
    op.add_column(
        "ambassador_campaigns",
        sa.Column(
            "created_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_ambassador_campaigns_source",
        "ambassador_campaigns",
        ["source"],
    )

    op.add_column(
        "ambassador_sales",
        sa.Column(
            "reversed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "ambassador_sales",
        sa.Column(
            "reversed_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "ambassador_sales",
        sa.Column("reversal_reason", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "ambassador_sales",
        sa.Column(
            "reward_status_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "ambassador_sales",
        sa.Column(
            "reward_status_updated_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("ambassador_sales", "reward_status_updated_by_user_id")
    op.drop_column("ambassador_sales", "reward_status_updated_at")
    op.drop_column("ambassador_sales", "reversal_reason")
    op.drop_column("ambassador_sales", "reversed_by_user_id")
    op.drop_column("ambassador_sales", "reversed_at")
    op.drop_index("ix_ambassador_campaigns_source", table_name="ambassador_campaigns")
    op.drop_column("ambassador_campaigns", "created_by_user_id")
    op.drop_column("ambassador_campaigns", "source")
    op.drop_table("ambassador_platform_settings")
