"""advanced analytics tracking tables

Revision ID: 20260716_0013
Revises: 20260716_0012
Create Date: 2026-07-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260716_0013"
down_revision: Union[str, Sequence[str], None] = "20260716_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analytics_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_name", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("host_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("properties", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analytics_events_event_name", "analytics_events", ["event_name"])
    op.create_index("ix_analytics_events_host_id", "analytics_events", ["host_id"])
    op.create_index("ix_analytics_events_user_id", "analytics_events", ["user_id"])
    op.create_index("ix_analytics_events_session_id", "analytics_events", ["session_id"])
    op.create_index("ix_analytics_events_created_at", "analytics_events", ["created_at"])
    op.create_index(
        "ix_analytics_events_name_created",
        "analytics_events",
        ["event_name", "created_at"],
    )
    op.create_index(
        "ix_analytics_events_host_created",
        "analytics_events",
        ["host_id", "created_at"],
    )
    op.create_index(
        "ix_analytics_events_entity",
        "analytics_events",
        ["entity_type", "entity_id"],
    )

    op.create_table(
        "page_views",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=True),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("referrer", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_page_views_host_id", "page_views", ["host_id"])
    op.create_index("ix_page_views_event_id", "page_views", ["event_id"])
    op.create_index("ix_page_views_session_id", "page_views", ["session_id"])
    op.create_index("ix_page_views_created_at", "page_views", ["created_at"])
    op.create_index("ix_page_views_path_created", "page_views", ["path", "created_at"])
    op.create_index("ix_page_views_host_created", "page_views", ["host_id", "created_at"])
    op.create_index(
        "ix_page_views_event_created", "page_views", ["event_id", "created_at"]
    )

    op.create_table(
        "event_impressions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_event_impressions_event_id", "event_impressions", ["event_id"])
    op.create_index("ix_event_impressions_host_id", "event_impressions", ["host_id"])
    op.create_index(
        "ix_event_impressions_session_id", "event_impressions", ["session_id"]
    )
    op.create_index(
        "ix_event_impressions_created_at", "event_impressions", ["created_at"]
    )
    op.create_index(
        "ix_event_impressions_event_created",
        "event_impressions",
        ["event_id", "created_at"],
    )
    op.create_index(
        "ix_event_impressions_host_created",
        "event_impressions",
        ["host_id", "created_at"],
    )

    op.create_table(
        "event_clicks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("click_target", sa.String(length=120), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_event_clicks_event_id", "event_clicks", ["event_id"])
    op.create_index("ix_event_clicks_host_id", "event_clicks", ["host_id"])
    op.create_index("ix_event_clicks_session_id", "event_clicks", ["session_id"])
    op.create_index("ix_event_clicks_created_at", "event_clicks", ["created_at"])
    op.create_index(
        "ix_event_clicks_event_created", "event_clicks", ["event_id", "created_at"]
    )
    op.create_index(
        "ix_event_clicks_host_created", "event_clicks", ["host_id", "created_at"]
    )

    op.create_table(
        "conversion_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("host_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversion_events_event_id", "conversion_events", ["event_id"])
    op.create_index("ix_conversion_events_host_id", "conversion_events", ["host_id"])
    op.create_index("ix_conversion_events_session_id", "conversion_events", ["session_id"])
    op.create_index("ix_conversion_events_stage", "conversion_events", ["stage"])
    op.create_index(
        "ix_conversion_events_created_at", "conversion_events", ["created_at"]
    )
    op.create_index(
        "ix_conversion_events_event_stage_created",
        "conversion_events",
        ["event_id", "stage", "created_at"],
    )
    op.create_index(
        "ix_conversion_events_host_stage_created",
        "conversion_events",
        ["host_id", "stage", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("conversion_events")
    op.drop_table("event_clicks")
    op.drop_table("event_impressions")
    op.drop_table("page_views")
    op.drop_table("analytics_events")
