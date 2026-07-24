"""Ambassador domain tables (profiles, participants, clicks, attributions,
conversions, payouts, audit) + campaign column extensions.

Revision ID: 20260719_0084
Revises: 20260719_0083
Create Date: 2026-07-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260719_0084"
down_revision = "20260719_0083"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Extend ambassador_campaigns toward phase-9 shape (keep v1 rows) ---
    op.add_column(
        "ambassador_campaigns",
        sa.Column("host_profile_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "ambassador_campaigns",
        sa.Column("merch_product_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "ambassador_campaigns",
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.add_column(
        "ambassador_campaigns",
        sa.Column(
            "visibility",
            sa.String(length=32),
            nullable=False,
            server_default="public_open",
        ),
    )
    op.add_column(
        "ambassador_campaigns",
        sa.Column(
            "cookie_window_days",
            sa.Integer(),
            nullable=False,
            server_default="30",
        ),
    )
    op.create_foreign_key(
        "fk_ambassador_campaigns_host_profile_id",
        "ambassador_campaigns",
        "host_profiles",
        ["host_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_ambassador_campaigns_merch_product_id",
        "ambassador_campaigns",
        "event_merch_products",
        ["merch_product_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_ambassador_campaigns_host_profile_id",
        "ambassador_campaigns",
        ["host_profile_id"],
    )
    op.create_index(
        "ix_ambassador_campaigns_merch_product_id",
        "ambassador_campaigns",
        ["merch_product_id"],
    )
    op.create_index(
        "ix_ambassador_campaigns_visibility",
        "ambassador_campaigns",
        ["visibility"],
    )

    op.execute(
        sa.text(
            """
            UPDATE ambassador_campaigns AS c
            SET host_profile_id = hp.id
            FROM host_profiles AS hp
            WHERE hp.host_id = c.host_id
              AND c.host_profile_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE ambassador_campaigns
            SET visibility = CASE
                WHEN status = 'public_open' THEN 'public_open'
                WHEN status = 'paused' THEN 'public_open'
                ELSE 'private'
            END
            """
        )
    )

    op.alter_column("ambassador_campaigns", "host_id", nullable=True)
    op.alter_column("ambassador_campaigns", "event_id", nullable=True)

    # --- ambassador_profiles ---
    op.create_table(
        "ambassador_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="active",
        ),
        sa.Column("public_code_base", sa.String(length=64), nullable=True),
        sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_ambassador_profiles_user_id"),
    )
    op.create_index(
        "ix_ambassador_profiles_user_id", "ambassador_profiles", ["user_id"]
    )
    op.create_index(
        "ix_ambassador_profiles_status", "ambassador_profiles", ["status"]
    )

    # --- ambassador_participants ---
    op.create_table(
        "ambassador_participants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("ambassador_profile_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("ambassador_code", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "joined_at",
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
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["ambassador_campaigns.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["ambassador_profile_id"],
            ["ambassador_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id",
            "ambassador_profile_id",
            name="uq_ambassador_participants_campaign_profile",
        ),
        sa.UniqueConstraint(
            "campaign_id",
            "ambassador_code",
            name="uq_ambassador_participants_campaign_code",
        ),
    )
    op.create_index(
        "ix_ambassador_participants_campaign_id",
        "ambassador_participants",
        ["campaign_id"],
    )
    op.create_index(
        "ix_ambassador_participants_ambassador_profile_id",
        "ambassador_participants",
        ["ambassador_profile_id"],
    )
    op.create_index(
        "ix_ambassador_participants_user_id",
        "ambassador_participants",
        ["user_id"],
    )
    op.create_index(
        "ix_ambassador_participants_status",
        "ambassador_participants",
        ["status"],
    )

    # --- ambassador_clicks ---
    op.create_table(
        "ambassador_clicks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("merch_product_id", sa.Uuid(), nullable=True),
        sa.Column("session_id", sa.String(length=128), nullable=True),
        sa.Column("visitor_fingerprint_hash", sa.String(length=128), nullable=True),
        sa.Column("ip_hash", sa.String(length=128), nullable=True),
        sa.Column("user_agent_hash", sa.String(length=128), nullable=True),
        sa.Column("landing_url", sa.String(length=1000), nullable=False),
        sa.Column("referrer_url", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["ambassador_campaigns.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["participant_id"],
            ["ambassador_participants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["merch_product_id"],
            ["event_merch_products.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ambassador_clicks_campaign_id", "ambassador_clicks", ["campaign_id"]
    )
    op.create_index(
        "ix_ambassador_clicks_participant_id",
        "ambassador_clicks",
        ["participant_id"],
    )
    op.create_index(
        "ix_ambassador_clicks_event_id", "ambassador_clicks", ["event_id"]
    )
    op.create_index(
        "ix_ambassador_clicks_merch_product_id",
        "ambassador_clicks",
        ["merch_product_id"],
    )
    op.create_index(
        "ix_ambassador_clicks_session_id", "ambassador_clicks", ["session_id"]
    )
    op.create_index(
        "ix_ambassador_clicks_created_at", "ambassador_clicks", ["created_at"]
    )
    op.create_index(
        "ix_ambassador_clicks_campaign_created",
        "ambassador_clicks",
        ["campaign_id", "created_at"],
    )
    op.create_index(
        "ix_ambassador_clicks_participant_created",
        "ambassador_clicks",
        ["participant_id", "created_at"],
    )

    # --- ambassador_attributions ---
    op.create_table(
        "ambassador_attributions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("session_id", sa.String(length=128), nullable=True),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("merch_product_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["ambassador_campaigns.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["participant_id"],
            ["ambassador_participants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["merch_product_id"],
            ["event_merch_products.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ambassador_attributions_campaign_id",
        "ambassador_attributions",
        ["campaign_id"],
    )
    op.create_index(
        "ix_ambassador_attributions_participant_id",
        "ambassador_attributions",
        ["participant_id"],
    )
    op.create_index(
        "ix_ambassador_attributions_user_id",
        "ambassador_attributions",
        ["user_id"],
    )
    op.create_index(
        "ix_ambassador_attributions_session_id",
        "ambassador_attributions",
        ["session_id"],
    )
    op.create_index(
        "ix_ambassador_attributions_event_id",
        "ambassador_attributions",
        ["event_id"],
    )
    op.create_index(
        "ix_ambassador_attributions_merch_product_id",
        "ambassador_attributions",
        ["merch_product_id"],
    )
    op.create_index(
        "ix_ambassador_attributions_source",
        "ambassador_attributions",
        ["source"],
    )
    op.create_index(
        "ix_ambassador_attributions_expires_at",
        "ambassador_attributions",
        ["expires_at"],
    )
    op.create_index(
        "ix_ambassador_attributions_session_expires",
        "ambassador_attributions",
        ["session_id", "expires_at"],
    )
    op.create_index(
        "ix_ambassador_attributions_user_expires",
        "ambassador_attributions",
        ["user_id", "expires_at"],
    )

    # --- ambassador_conversions ---
    op.create_table(
        "ambassador_conversions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("buyer_user_id", sa.Uuid(), nullable=True),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("ticket_id", sa.Uuid(), nullable=True),
        sa.Column("merch_order_id", sa.Uuid(), nullable=True),
        sa.Column("conversion_type", sa.String(length=32), nullable=False),
        sa.Column("gross_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "eligible_amount", sa.Numeric(precision=12, scale=2), nullable=False
        ),
        sa.Column(
            "commission_amount",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("dedupe_key", sa.String(length=200), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
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
            ["campaign_id"], ["ambassador_campaigns.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["participant_id"],
            ["ambassador_participants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["buyer_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["merch_order_id"], ["orders.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dedupe_key", name="uq_ambassador_conversions_dedupe_key"
        ),
    )
    op.create_index(
        "ix_ambassador_conversions_campaign_id",
        "ambassador_conversions",
        ["campaign_id"],
    )
    op.create_index(
        "ix_ambassador_conversions_participant_id",
        "ambassador_conversions",
        ["participant_id"],
    )
    op.create_index(
        "ix_ambassador_conversions_buyer_user_id",
        "ambassador_conversions",
        ["buyer_user_id"],
    )
    op.create_index(
        "ix_ambassador_conversions_order_id",
        "ambassador_conversions",
        ["order_id"],
    )
    op.create_index(
        "ix_ambassador_conversions_ticket_id",
        "ambassador_conversions",
        ["ticket_id"],
    )
    op.create_index(
        "ix_ambassador_conversions_merch_order_id",
        "ambassador_conversions",
        ["merch_order_id"],
    )
    op.create_index(
        "ix_ambassador_conversions_conversion_type",
        "ambassador_conversions",
        ["conversion_type"],
    )
    op.create_index(
        "ix_ambassador_conversions_status",
        "ambassador_conversions",
        ["status"],
    )
    op.create_index(
        "ix_ambassador_conversions_created_at",
        "ambassador_conversions",
        ["created_at"],
    )
    op.create_index(
        "ix_ambassador_conversions_campaign_status",
        "ambassador_conversions",
        ["campaign_id", "status"],
    )

    # --- ambassador_payouts ---
    op.create_table(
        "ambassador_payouts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ambassador_profile_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("payout_method", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
            ["ambassador_profile_id"],
            ["ambassador_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ambassador_payouts_ambassador_profile_id",
        "ambassador_payouts",
        ["ambassador_profile_id"],
    )
    op.create_index(
        "ix_ambassador_payouts_user_id", "ambassador_payouts", ["user_id"]
    )
    op.create_index(
        "ix_ambassador_payouts_status", "ambassador_payouts", ["status"]
    )
    op.create_index(
        "ix_ambassador_payouts_created_at", "ambassador_payouts", ["created_at"]
    )

    # --- ambassador_audit_logs ---
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.create_table(
        "ambassador_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", json_type, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ambassador_audit_logs_actor_user_id",
        "ambassador_audit_logs",
        ["actor_user_id"],
    )
    op.create_index(
        "ix_ambassador_audit_logs_action", "ambassador_audit_logs", ["action"]
    )
    op.create_index(
        "ix_ambassador_audit_logs_created_at",
        "ambassador_audit_logs",
        ["created_at"],
    )
    op.create_index(
        "ix_ambassador_audit_logs_entity",
        "ambassador_audit_logs",
        ["entity_type", "entity_id"],
    )


def downgrade() -> None:
    op.drop_table("ambassador_audit_logs")
    op.drop_table("ambassador_payouts")
    op.drop_table("ambassador_conversions")
    op.drop_table("ambassador_attributions")
    op.drop_table("ambassador_clicks")
    op.drop_table("ambassador_participants")
    op.drop_table("ambassador_profiles")

    op.drop_index("ix_ambassador_campaigns_visibility", table_name="ambassador_campaigns")
    op.drop_index(
        "ix_ambassador_campaigns_merch_product_id", table_name="ambassador_campaigns"
    )
    op.drop_index(
        "ix_ambassador_campaigns_host_profile_id", table_name="ambassador_campaigns"
    )
    op.drop_constraint(
        "fk_ambassador_campaigns_merch_product_id",
        "ambassador_campaigns",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_ambassador_campaigns_host_profile_id",
        "ambassador_campaigns",
        type_="foreignkey",
    )
    op.drop_column("ambassador_campaigns", "cookie_window_days")
    op.drop_column("ambassador_campaigns", "visibility")
    op.drop_column("ambassador_campaigns", "description")
    op.drop_column("ambassador_campaigns", "merch_product_id")
    op.drop_column("ambassador_campaigns", "host_profile_id")

    # Restore NOT NULL only when every row still has values (v1 expectation).
    op.execute(
        sa.text(
            """
            UPDATE ambassador_campaigns
            SET host_id = (
                SELECT hp.host_id FROM host_profiles hp
                WHERE hp.id = ambassador_campaigns.host_profile_id
            )
            WHERE host_id IS NULL AND host_profile_id IS NOT NULL
            """
        )
    )
    op.alter_column("ambassador_campaigns", "host_id", nullable=False)
    op.alter_column("ambassador_campaigns", "event_id", nullable=False)
