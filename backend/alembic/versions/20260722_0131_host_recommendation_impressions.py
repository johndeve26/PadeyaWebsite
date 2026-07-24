"""Alembic: host recommendation impressions and category hides."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260722_0131"
down_revision = "20260722_0130"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "host_recommendation_impressions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("surface", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("recommendation_score", sa.Integer(), nullable=True),
        sa.Column(
            "reason_codes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "shown_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_host_recommendation_impressions_user_id"),
        "host_recommendation_impressions",
        ["user_id"],
    )
    op.create_index(
        op.f("ix_host_recommendation_impressions_host_id"),
        "host_recommendation_impressions",
        ["host_id"],
    )
    op.create_index(
        "ix_host_recommendation_impressions_user_shown",
        "host_recommendation_impressions",
        ["user_id", "shown_at"],
    )
    op.create_index(
        "ix_host_recommendation_impressions_user_host",
        "host_recommendation_impressions",
        ["user_id", "host_id"],
    )

    op.create_table(
        "host_recommendation_category_hides",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category_slug", sa.String(length=120), nullable=False),
        sa.Column(
            "hidden_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "category_slug",
            name="uq_host_recommendation_category_hides_pair",
        ),
    )
    op.create_index(
        op.f("ix_host_recommendation_category_hides_user_id"),
        "host_recommendation_category_hides",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_host_recommendation_category_hides_user_id"),
        table_name="host_recommendation_category_hides",
    )
    op.drop_table("host_recommendation_category_hides")
    op.drop_index(
        "ix_host_recommendation_impressions_user_host",
        table_name="host_recommendation_impressions",
    )
    op.drop_index(
        "ix_host_recommendation_impressions_user_shown",
        table_name="host_recommendation_impressions",
    )
    op.drop_index(
        op.f("ix_host_recommendation_impressions_host_id"),
        table_name="host_recommendation_impressions",
    )
    op.drop_index(
        op.f("ix_host_recommendation_impressions_user_id"),
        table_name="host_recommendation_impressions",
    )
    op.drop_table("host_recommendation_impressions")
