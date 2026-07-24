"""legacy tiers and score history

Revision ID: 20260716_0006
Revises: 20260716_0005
Create Date: 2026-07-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260716_0006"
down_revision: Union[str, Sequence[str], None] = "20260716_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "legacy_tiers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("min_score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("requirements", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_legacy_tiers_slug"),
    )
    op.create_index("ix_legacy_tiers_slug", "legacy_tiers", ["slug"], unique=False)
    op.create_index("ix_legacy_tiers_rank", "legacy_tiers", ["rank"], unique=False)

    op.add_column("host_legacy_scores", sa.Column("tier_id", sa.Uuid(), nullable=True))
    op.add_column(
        "host_legacy_scores",
        sa.Column("completed_events", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "host_legacy_scores",
        sa.Column(
            "composite_score",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column("host_legacy_scores", sa.Column("factor_scores", sa.JSON(), nullable=True))
    op.create_foreign_key(
        "fk_host_legacy_scores_tier_id",
        "host_legacy_scores",
        "legacy_tiers",
        ["tier_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_host_legacy_scores_tier_id", "host_legacy_scores", ["tier_id"], unique=False)

    op.create_table(
        "host_legacy_score_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("tier_id", sa.Uuid(), nullable=True),
        sa.Column("previous_tier_slug", sa.String(length=64), nullable=True),
        sa.Column("tier_slug", sa.String(length=64), nullable=False),
        sa.Column("composite_score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("previous_composite_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("factor_scores", sa.JSON(), nullable=True),
        sa.Column("metrics_snapshot", sa.JSON(), nullable=True),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tier_id"], ["legacy_tiers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_host_legacy_score_history_host_id",
        "host_legacy_score_history",
        ["host_id"],
        unique=False,
    )
    op.create_index(
        "ix_host_legacy_score_history_tier_id",
        "host_legacy_score_history",
        ["tier_id"],
        unique=False,
    )
    op.create_index(
        "ix_host_legacy_score_history_reason",
        "host_legacy_score_history",
        ["reason"],
        unique=False,
    )
    op.create_index(
        "ix_host_legacy_score_history_created_at",
        "host_legacy_score_history",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_host_legacy_score_history_created_at", table_name="host_legacy_score_history")
    op.drop_index("ix_host_legacy_score_history_reason", table_name="host_legacy_score_history")
    op.drop_index("ix_host_legacy_score_history_tier_id", table_name="host_legacy_score_history")
    op.drop_index("ix_host_legacy_score_history_host_id", table_name="host_legacy_score_history")
    op.drop_table("host_legacy_score_history")

    op.drop_index("ix_host_legacy_scores_tier_id", table_name="host_legacy_scores")
    op.drop_constraint("fk_host_legacy_scores_tier_id", "host_legacy_scores", type_="foreignkey")
    op.drop_column("host_legacy_scores", "factor_scores")
    op.drop_column("host_legacy_scores", "composite_score")
    op.drop_column("host_legacy_scores", "completed_events")
    op.drop_column("host_legacy_scores", "tier_id")

    op.drop_index("ix_legacy_tiers_rank", table_name="legacy_tiers")
    op.drop_index("ix_legacy_tiers_slug", table_name="legacy_tiers")
    op.drop_table("legacy_tiers")
