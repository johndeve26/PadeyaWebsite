"""Add dimension columns to analytics_events for industry-standard tracking.

Revision ID: 20260717_0021
Revises: 20260717_0020
Create Date: 2026-07-17
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260717_0021"
down_revision: Union[str, Sequence[str], None] = "20260717_0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "analytics_events",
        sa.Column("target_event_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.add_column(
        "analytics_events",
        sa.Column("anonymous_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "analytics_events",
        sa.Column("request_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "analytics_events",
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "analytics_events",
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "analytics_events", sa.Column("source", sa.String(length=120), nullable=True)
    )
    op.add_column(
        "analytics_events", sa.Column("medium", sa.String(length=120), nullable=True)
    )
    op.add_column(
        "analytics_events", sa.Column("campaign", sa.String(length=160), nullable=True)
    )
    op.add_column(
        "analytics_events", sa.Column("term", sa.String(length=160), nullable=True)
    )
    op.add_column(
        "analytics_events", sa.Column("content", sa.String(length=160), nullable=True)
    )
    op.add_column(
        "analytics_events", sa.Column("referrer", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "analytics_events",
        sa.Column("landing_page", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "analytics_events",
        sa.Column("current_path", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "analytics_events",
        sa.Column("previous_path", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "analytics_events", sa.Column("user_agent", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "analytics_events",
        sa.Column("device_type", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "analytics_events", sa.Column("browser", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "analytics_events", sa.Column("os", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "analytics_events", sa.Column("country", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "analytics_events", sa.Column("city", sa.String(length=96), nullable=True)
    )
    op.add_column(
        "analytics_events", sa.Column("ip_hash", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "analytics_events",
        sa.Column(
            "metadata",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "analytics_events",
        sa.Column(
            "is_bot", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
    )
    op.add_column(
        "analytics_events",
        sa.Column("environment", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "analytics_events",
        sa.Column("app_version", sa.String(length=64), nullable=True),
    )

    op.create_foreign_key(
        "fk_analytics_events_target_event_id",
        "analytics_events",
        "events",
        ["target_event_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_analytics_events_target_event_id", "analytics_events", ["target_event_id"]
    )
    op.create_index(
        "ix_analytics_events_anonymous_id", "analytics_events", ["anonymous_id"]
    )
    op.create_index(
        "ix_analytics_events_request_id", "analytics_events", ["request_id"], unique=True
    )
    op.create_index(
        "ix_analytics_events_occurred_at", "analytics_events", ["occurred_at"]
    )
    op.create_index(
        "ix_analytics_events_received_at", "analytics_events", ["received_at"]
    )
    op.create_index(
        "ix_analytics_events_source_campaign",
        "analytics_events",
        ["source", "campaign"],
    )
    op.create_index(
        "ix_analytics_events_device_type", "analytics_events", ["device_type"]
    )


def downgrade() -> None:
    op.drop_index("ix_analytics_events_device_type", table_name="analytics_events")
    op.drop_index("ix_analytics_events_source_campaign", table_name="analytics_events")
    op.drop_index("ix_analytics_events_received_at", table_name="analytics_events")
    op.drop_index("ix_analytics_events_occurred_at", table_name="analytics_events")
    op.drop_index("ix_analytics_events_request_id", table_name="analytics_events")
    op.drop_index("ix_analytics_events_anonymous_id", table_name="analytics_events")
    op.drop_index("ix_analytics_events_target_event_id", table_name="analytics_events")
    op.drop_constraint(
        "fk_analytics_events_target_event_id", "analytics_events", type_="foreignkey"
    )
    for col in (
        "app_version",
        "environment",
        "is_bot",
        "metadata",
        "ip_hash",
        "city",
        "country",
        "os",
        "browser",
        "device_type",
        "user_agent",
        "previous_path",
        "current_path",
        "landing_page",
        "referrer",
        "content",
        "term",
        "campaign",
        "medium",
        "source",
        "received_at",
        "occurred_at",
        "request_id",
        "anonymous_id",
        "target_event_id",
    ):
        op.drop_column("analytics_events", col)
