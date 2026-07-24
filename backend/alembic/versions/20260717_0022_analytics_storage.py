"""Extend analytics_events storage + add rollup/dedupe tables.

Revision ID: 20260717_0022
Revises: 20260717_0021
Create Date: 2026-07-17
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260717_0022"
down_revision: Union[str, Sequence[str], None] = "20260717_0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Extend analytics_events (backwards-compatible) ---
    op.add_column(
        "analytics_events", sa.Column("path", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "analytics_events",
        sa.Column("utm_source", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "analytics_events",
        sa.Column("utm_medium", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "analytics_events",
        sa.Column("utm_campaign", sa.String(length=160), nullable=True),
    )
    op.add_column(
        "analytics_events", sa.Column("utm_term", sa.String(length=160), nullable=True)
    )
    op.add_column(
        "analytics_events",
        sa.Column("utm_content", sa.String(length=160), nullable=True),
    )
    op.add_column(
        "analytics_events",
        sa.Column("user_agent_hash", sa.String(length=64), nullable=True),
    )

    # Backfill mirrors from existing columns
    op.execute(
        sa.text(
            """
            UPDATE analytics_events
            SET
              path = COALESCE(path, current_path),
              utm_source = COALESCE(utm_source, source),
              utm_medium = COALESCE(utm_medium, medium),
              utm_campaign = COALESCE(utm_campaign, campaign),
              utm_term = COALESCE(utm_term, term),
              utm_content = COALESCE(utm_content, content)
            """
        )
    )

    op.create_index(
        "ix_analytics_events_name_occurred",
        "analytics_events",
        ["event_name", "occurred_at"],
    )
    op.create_index(
        "ix_analytics_events_host_occurred",
        "analytics_events",
        ["host_id", "occurred_at"],
    )
    op.create_index(
        "ix_analytics_events_target_occurred",
        "analytics_events",
        ["target_event_id", "occurred_at"],
    )
    op.create_index(
        "ix_analytics_events_session_occurred",
        "analytics_events",
        ["session_id", "occurred_at"],
    )
    op.create_index(
        "ix_analytics_events_anonymous_occurred",
        "analytics_events",
        ["anonymous_id", "occurred_at"],
    )
    op.create_index(
        "ix_analytics_events_user_occurred",
        "analytics_events",
        ["user_id", "occurred_at"],
    )
    op.create_index(
        "ix_analytics_events_utm_source_campaign",
        "analytics_events",
        ["utm_source", "utm_campaign"],
    )

    # Expression index for ticket_type_id in metadata (PostgreSQL only)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.create_index(
            "ix_analytics_events_meta_ticket_type_id",
            "analytics_events",
            [sa.text("(metadata->>'ticket_type_id')")],
            postgresql_using="btree",
        )

    # --- event_daily_analytics ---
    op.create_table(
        "event_daily_analytics",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("event_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("host_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("impressions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("unique_impressions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("card_clicks", sa.Integer(), server_default="0", nullable=False),
        sa.Column("detail_views", sa.Integer(), server_default="0", nullable=False),
        sa.Column("unique_detail_views", sa.Integer(), server_default="0", nullable=False),
        sa.Column("ticket_panel_views", sa.Integer(), server_default="0", nullable=False),
        sa.Column("ticket_selections", sa.Integer(), server_default="0", nullable=False),
        sa.Column("checkout_starts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("payment_starts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("payment_successes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("payment_failures", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tickets_sold", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "gross_revenue",
            sa.Numeric(14, 2),
            server_default="0",
            nullable=False,
        ),
        sa.Column("net_revenue", sa.Numeric(14, 2), nullable=True),
        sa.Column("promo_uses", sa.Integer(), server_default="0", nullable=False),
        sa.Column("ambassador_sales", sa.Integer(), server_default="0", nullable=False),
        sa.Column("shares", sa.Integer(), server_default="0", nullable=False),
        sa.Column("saves", sa.Integer(), server_default="0", nullable=False),
        sa.Column("follows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("reviews_submitted", sa.Integer(), server_default="0", nullable=False),
        sa.Column("checkins", sa.Integer(), server_default="0", nullable=False),
        sa.Column("conversion_impression_to_view", sa.Numeric(8, 6), nullable=True),
        sa.Column("conversion_view_to_checkout", sa.Numeric(8, 6), nullable=True),
        sa.Column("conversion_checkout_to_purchase", sa.Numeric(8, 6), nullable=True),
        sa.Column("conversion_view_to_purchase", sa.Numeric(8, 6), nullable=True),
        sa.Column(
            "recalculated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
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
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("date", "event_id", name="uq_event_daily_analytics_date_event"),
    )
    op.create_index(
        "ix_event_daily_analytics_event_date",
        "event_daily_analytics",
        ["event_id", "date"],
    )
    op.create_index(
        "ix_event_daily_analytics_host_date",
        "event_daily_analytics",
        ["host_id", "date"],
    )
    op.create_index("ix_event_daily_analytics_date", "event_daily_analytics", ["date"])

    # --- event_source_analytics ---
    op.create_table(
        "event_source_analytics",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("event_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("medium", sa.String(length=120), nullable=False),
        sa.Column("campaign", sa.String(length=160), nullable=False),
        sa.Column("impressions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("clicks", sa.Integer(), server_default="0", nullable=False),
        sa.Column("views", sa.Integer(), server_default="0", nullable=False),
        sa.Column("checkout_starts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("purchases", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tickets_sold", sa.Integer(), server_default="0", nullable=False),
        sa.Column("revenue", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("conversion_rate", sa.Numeric(8, 6), nullable=True),
        sa.Column(
            "recalculated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
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
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "date",
            "event_id",
            "source",
            "medium",
            "campaign",
            name="uq_event_source_analytics_dims",
        ),
    )
    op.create_index(
        "ix_event_source_analytics_event_date",
        "event_source_analytics",
        ["event_id", "date"],
    )
    op.create_index(
        "ix_event_source_analytics_source_date",
        "event_source_analytics",
        ["source", "date"],
    )

    # --- event_ticket_type_analytics ---
    op.create_table(
        "event_ticket_type_analytics",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("event_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("ticket_type_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("impressions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("selections", sa.Integer(), server_default="0", nullable=False),
        sa.Column("checkout_starts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tickets_sold", sa.Integer(), server_default="0", nullable=False),
        sa.Column("revenue", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("conversion_rate", sa.Numeric(8, 6), nullable=True),
        sa.Column(
            "recalculated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
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
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["ticket_type_id"], ["ticket_types.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "date",
            "event_id",
            "ticket_type_id",
            name="uq_event_ticket_type_analytics_dims",
        ),
    )
    op.create_index(
        "ix_event_ticket_type_analytics_event_date",
        "event_ticket_type_analytics",
        ["event_id", "date"],
    )
    op.create_index(
        "ix_event_ticket_type_analytics_ticket_date",
        "event_ticket_type_analytics",
        ["ticket_type_id", "date"],
    )

    # --- event_geo_device_analytics ---
    op.create_table(
        "event_geo_device_analytics",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("event_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("country", sa.String(length=64), nullable=False),
        sa.Column("city", sa.String(length=96), nullable=False),
        sa.Column("device_type", sa.String(length=32), nullable=False),
        sa.Column("browser", sa.String(length=64), nullable=False),
        sa.Column("views", sa.Integer(), server_default="0", nullable=False),
        sa.Column("checkout_starts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("purchases", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tickets_sold", sa.Integer(), server_default="0", nullable=False),
        sa.Column("revenue", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column(
            "recalculated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
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
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "date",
            "event_id",
            "country",
            "city",
            "device_type",
            "browser",
            name="uq_event_geo_device_analytics_dims",
        ),
    )
    op.create_index(
        "ix_event_geo_device_analytics_event_date",
        "event_geo_device_analytics",
        ["event_id", "date"],
    )
    op.create_index(
        "ix_event_geo_device_analytics_country_date",
        "event_geo_device_analytics",
        ["country", "date"],
    )
    op.create_index(
        "ix_event_geo_device_analytics_device_date",
        "event_geo_device_analytics",
        ["device_type", "date"],
    )

    # --- analytics_dedupe_keys ---
    op.create_table(
        "analytics_dedupe_keys",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("dedupe_key", sa.String(length=191), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("target_event_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("anonymous_id", sa.String(length=64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["target_event_id"], ["events.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("dedupe_key", name="uq_analytics_dedupe_keys_key"),
    )
    op.create_index(
        "ix_analytics_dedupe_keys_scope", "analytics_dedupe_keys", ["scope"]
    )
    op.create_index(
        "ix_analytics_dedupe_keys_created_at",
        "analytics_dedupe_keys",
        ["created_at"],
    )
    op.create_index(
        "ix_analytics_dedupe_keys_scope_created",
        "analytics_dedupe_keys",
        ["scope", "created_at"],
    )
    op.create_index(
        "ix_analytics_dedupe_keys_event_created",
        "analytics_dedupe_keys",
        ["target_event_id", "created_at"],
    )
    op.create_index(
        "ix_analytics_dedupe_keys_expires",
        "analytics_dedupe_keys",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_table("analytics_dedupe_keys")
    op.drop_table("event_geo_device_analytics")
    op.drop_table("event_ticket_type_analytics")
    op.drop_table("event_source_analytics")
    op.drop_table("event_daily_analytics")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index(
            "ix_analytics_events_meta_ticket_type_id", table_name="analytics_events"
        )

    op.drop_index("ix_analytics_events_utm_source_campaign", table_name="analytics_events")
    op.drop_index("ix_analytics_events_user_occurred", table_name="analytics_events")
    op.drop_index("ix_analytics_events_anonymous_occurred", table_name="analytics_events")
    op.drop_index("ix_analytics_events_session_occurred", table_name="analytics_events")
    op.drop_index("ix_analytics_events_target_occurred", table_name="analytics_events")
    op.drop_index("ix_analytics_events_host_occurred", table_name="analytics_events")
    op.drop_index("ix_analytics_events_name_occurred", table_name="analytics_events")

    op.drop_column("analytics_events", "user_agent_hash")
    op.drop_column("analytics_events", "utm_content")
    op.drop_column("analytics_events", "utm_term")
    op.drop_column("analytics_events", "utm_campaign")
    op.drop_column("analytics_events", "utm_medium")
    op.drop_column("analytics_events", "utm_source")
    op.drop_column("analytics_events", "path")
