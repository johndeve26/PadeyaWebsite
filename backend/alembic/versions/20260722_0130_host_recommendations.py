"""Alembic: fan host recommendation dismissals and feedback."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260722_0130"
down_revision = "20260722_0129"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "host_recommendation_dismissals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=120), nullable=True),
        sa.Column(
            "dismissed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "host_id",
            name="uq_host_recommendation_dismissals_pair",
        ),
    )
    op.create_index(
        op.f("ix_host_recommendation_dismissals_user_id"),
        "host_recommendation_dismissals",
        ["user_id"],
    )
    op.create_index(
        op.f("ix_host_recommendation_dismissals_host_id"),
        "host_recommendation_dismissals",
        ["host_id"],
    )
    op.create_index(
        "ix_host_recommendation_dismissals_user_dismissed",
        "host_recommendation_dismissals",
        ["user_id", "dismissed_at"],
    )

    op.create_table(
        "host_recommendation_feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column(
            "context",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_host_recommendation_feedback_user_id"),
        "host_recommendation_feedback",
        ["user_id"],
    )
    op.create_index(
        op.f("ix_host_recommendation_feedback_host_id"),
        "host_recommendation_feedback",
        ["host_id"],
    )
    op.create_index(
        "ix_host_recommendation_feedback_user_created",
        "host_recommendation_feedback",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_host_recommendation_feedback_user_action",
        "host_recommendation_feedback",
        ["user_id", "action"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_host_recommendation_feedback_user_action",
        table_name="host_recommendation_feedback",
    )
    op.drop_index(
        "ix_host_recommendation_feedback_user_created",
        table_name="host_recommendation_feedback",
    )
    op.drop_index(
        op.f("ix_host_recommendation_feedback_host_id"),
        table_name="host_recommendation_feedback",
    )
    op.drop_index(
        op.f("ix_host_recommendation_feedback_user_id"),
        table_name="host_recommendation_feedback",
    )
    op.drop_table("host_recommendation_feedback")

    op.drop_index(
        "ix_host_recommendation_dismissals_user_dismissed",
        table_name="host_recommendation_dismissals",
    )
    op.drop_index(
        op.f("ix_host_recommendation_dismissals_host_id"),
        table_name="host_recommendation_dismissals",
    )
    op.drop_index(
        op.f("ix_host_recommendation_dismissals_user_id"),
        table_name="host_recommendation_dismissals",
    )
    op.drop_table("host_recommendation_dismissals")
