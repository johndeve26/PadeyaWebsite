"""Alembic: Fan Connect suggestion dismissals, feedback, location preferences."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260720_0106"
down_revision = "20260720_0105"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fan_connect_suggestion_dismissals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("target_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=120), nullable=True),
        sa.Column(
            "dismissed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "actor_user_id",
            "target_user_id",
            name="uq_fan_connect_suggestion_dismissals_pair",
        ),
    )
    op.create_index(
        op.f("ix_fan_connect_suggestion_dismissals_actor_user_id"),
        "fan_connect_suggestion_dismissals",
        ["actor_user_id"],
    )
    op.create_index(
        op.f("ix_fan_connect_suggestion_dismissals_target_user_id"),
        "fan_connect_suggestion_dismissals",
        ["target_user_id"],
    )
    op.create_index(
        op.f("ix_fan_connect_suggestion_dismissals_expires_at"),
        "fan_connect_suggestion_dismissals",
        ["expires_at"],
    )
    op.create_index(
        "ix_fan_connect_suggestion_dismissals_actor_dismissed",
        "fan_connect_suggestion_dismissals",
        ["actor_user_id", "dismissed_at"],
    )

    op.create_table(
        "fan_connect_suggestion_feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("target_user_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_fan_connect_suggestion_feedback_actor_user_id"),
        "fan_connect_suggestion_feedback",
        ["actor_user_id"],
    )
    op.create_index(
        op.f("ix_fan_connect_suggestion_feedback_target_user_id"),
        "fan_connect_suggestion_feedback",
        ["target_user_id"],
    )
    op.create_index(
        op.f("ix_fan_connect_suggestion_feedback_action"),
        "fan_connect_suggestion_feedback",
        ["action"],
    )
    op.create_index(
        "ix_fan_connect_suggestion_feedback_actor_created",
        "fan_connect_suggestion_feedback",
        ["actor_user_id", "created_at"],
    )
    op.create_index(
        "ix_fan_connect_suggestion_feedback_actor_action",
        "fan_connect_suggestion_feedback",
        ["actor_user_id", "action"],
    )

    op.create_table(
        "fan_connect_location_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("area", sa.String(length=120), nullable=True),
        sa.Column("country", sa.String(length=120), nullable=True),
        sa.Column("latitude_approx", sa.String(length=32), nullable=True),
        sa.Column("longitude_approx", sa.String(length=32), nullable=True),
        sa.Column("precision", sa.String(length=32), nullable=False),
        sa.Column(
            "consented_at",
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", name="uq_fan_connect_location_preferences_user"
        ),
    )
    op.create_index(
        op.f("ix_fan_connect_location_preferences_user_id"),
        "fan_connect_location_preferences",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_fan_connect_location_preferences_user_id"),
        table_name="fan_connect_location_preferences",
    )
    op.drop_table("fan_connect_location_preferences")
    op.drop_index(
        "ix_fan_connect_suggestion_feedback_actor_action",
        table_name="fan_connect_suggestion_feedback",
    )
    op.drop_index(
        "ix_fan_connect_suggestion_feedback_actor_created",
        table_name="fan_connect_suggestion_feedback",
    )
    op.drop_index(
        op.f("ix_fan_connect_suggestion_feedback_action"),
        table_name="fan_connect_suggestion_feedback",
    )
    op.drop_index(
        op.f("ix_fan_connect_suggestion_feedback_target_user_id"),
        table_name="fan_connect_suggestion_feedback",
    )
    op.drop_index(
        op.f("ix_fan_connect_suggestion_feedback_actor_user_id"),
        table_name="fan_connect_suggestion_feedback",
    )
    op.drop_table("fan_connect_suggestion_feedback")
    op.drop_index(
        "ix_fan_connect_suggestion_dismissals_actor_dismissed",
        table_name="fan_connect_suggestion_dismissals",
    )
    op.drop_index(
        op.f("ix_fan_connect_suggestion_dismissals_expires_at"),
        table_name="fan_connect_suggestion_dismissals",
    )
    op.drop_index(
        op.f("ix_fan_connect_suggestion_dismissals_target_user_id"),
        table_name="fan_connect_suggestion_dismissals",
    )
    op.drop_index(
        op.f("ix_fan_connect_suggestion_dismissals_actor_user_id"),
        table_name="fan_connect_suggestion_dismissals",
    )
    op.drop_table("fan_connect_suggestion_dismissals")
