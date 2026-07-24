"""Alembic: support ticket deflection tracking for guided Help-first flow.

Revision ID: 20260721_0111
Revises: 20260721_0110
Create Date: 2026-07-21

Stores pre-ticket help deflection events and attaches suggestion metadata
to support_cases when a ticket is opened after Help.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260721_0111"
down_revision = "20260721_0110"
branch_labels = None
depends_on = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.add_column(
        "support_cases",
        sa.Column(
            "help_suggestions_shown",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "support_cases",
        sa.Column("deflection_meta", JSON_TYPE, nullable=True),
    )

    op.create_table(
        "support_deflection_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("topic", sa.String(length=64), nullable=True),
        sa.Column("session_key", sa.String(length=64), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("article_id", sa.Uuid(), nullable=True),
        sa.Column("article_slug", sa.String(length=200), nullable=True),
        sa.Column("case_id", sa.Uuid(), nullable=True),
        sa.Column("meta", JSON_TYPE, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["case_id"], ["support_cases.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_support_deflection_events_event_type",
        "support_deflection_events",
        ["event_type"],
    )
    op.create_index(
        "ix_support_deflection_events_topic",
        "support_deflection_events",
        ["topic"],
    )
    op.create_index(
        "ix_support_deflection_events_created_at",
        "support_deflection_events",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_support_deflection_events_created_at",
        table_name="support_deflection_events",
    )
    op.drop_index(
        "ix_support_deflection_events_topic",
        table_name="support_deflection_events",
    )
    op.drop_index(
        "ix_support_deflection_events_event_type",
        table_name="support_deflection_events",
    )
    op.drop_table("support_deflection_events")
    op.drop_column("support_cases", "deflection_meta")
    op.drop_column("support_cases", "help_suggestions_shown")
