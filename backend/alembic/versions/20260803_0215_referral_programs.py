"""Unified referral programs: platform-wide + event-scoped parent linkage.

Revision ID: 20260803_0215
Revises: 20260802_0214
Create Date: 2026-08-03

Adds referral_programs / rules / exclusions, links existing campaigns,
payer_type + product_slice on ambassador_sales, nullable ambassador.host_id
for platform-wide enrollments. Backfills event-scoped programs without
rewriting financial history.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260803_0215"
down_revision = "20260802_0214"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "referral_programs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("public_description", sa.Text(), nullable=True),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("owner_type", sa.String(length=32), nullable=False),
        sa.Column(
            "owner_host_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hosts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column(
            "enrollment_mode",
            sa.String(length=32),
            nullable=False,
            server_default="manual_enrollment",
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "attribution_window_days", sa.Integer(), nullable=False, server_default="30"
        ),
        sa.Column(
            "default_landing_path",
            sa.String(length=500),
            nullable=False,
            server_default="/events",
        ),
        sa.Column("hold_period_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("budget_total", sa.Numeric(14, 2), nullable=True),
        sa.Column("per_ambassador_cap", sa.Numeric(14, 2), nullable=True),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
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
    )
    op.create_index("ix_referral_programs_scope", "referral_programs", ["scope"])
    op.create_index("ix_referral_programs_owner_type", "referral_programs", ["owner_type"])
    op.create_index("ix_referral_programs_status", "referral_programs", ["status"])
    op.create_index("ix_referral_programs_event_id", "referral_programs", ["event_id"])
    op.create_index(
        "ix_referral_programs_owner_host_id", "referral_programs", ["owner_host_id"]
    )

    op.create_table(
        "referral_program_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "program_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("referral_programs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("product_type", sa.String(length=32), nullable=False),
        sa.Column(
            "commission_mode",
            sa.String(length=32),
            nullable=False,
            server_default="percentage",
        ),
        sa.Column(
            "commission_value",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="5.00",
        ),
        sa.Column("maximum_commission_per_item", sa.Numeric(12, 2), nullable=True),
        sa.Column("minimum_order_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        sa.UniqueConstraint(
            "program_id",
            "product_type",
            name="uq_referral_program_rules_program_product",
        ),
    )
    op.create_index(
        "ix_referral_program_rules_program_id", "referral_program_rules", ["program_id"]
    )
    op.create_index(
        "ix_referral_program_rules_product_type",
        "referral_program_rules",
        ["product_type"],
    )

    op.create_table(
        "referral_program_exclusions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "program_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("referral_programs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "host_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hosts.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_referral_program_exclusions_program_id",
        "referral_program_exclusions",
        ["program_id"],
    )

    op.add_column(
        "ambassador_campaigns",
        sa.Column(
            "program_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("referral_programs.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_ambassador_campaigns_program_id", "ambassador_campaigns", ["program_id"]
    )

    op.add_column(
        "ambassadors",
        sa.Column(
            "program_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("referral_programs.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_ambassadors_program_id", "ambassadors", ["program_id"])
    op.alter_column(
        "ambassadors", "host_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True
    )
    op.create_index(
        "uq_ambassadors_platform_referral",
        "ambassadors",
        ["referral_code"],
        unique=True,
        postgresql_where=sa.text("program_kind = 'platform_wide'"),
    )

    op.add_column(
        "ambassador_sales",
        sa.Column(
            "payer_type",
            sa.String(length=32),
            nullable=False,
            server_default="host",
        ),
    )
    op.add_column(
        "ambassador_sales",
        sa.Column(
            "product_slice",
            sa.String(length=32),
            nullable=False,
            server_default="all",
        ),
    )
    op.add_column(
        "ambassador_sales",
        sa.Column(
            "program_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("referral_programs.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "ambassador_sales",
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
    )
    op.create_index("ix_ambassador_sales_payer_type", "ambassador_sales", ["payer_type"])
    op.create_index("ix_ambassador_sales_program_id", "ambassador_sales", ["program_id"])
    op.create_index(
        "uq_ambassador_sales_idempotency",
        "ambassador_sales",
        ["idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
    op.drop_constraint("uq_ambassador_sales_order_id", "ambassador_sales", type_="unique")
    op.create_index(
        "uq_ambassador_sales_order_slice",
        "ambassador_sales",
        ["order_id", "product_slice"],
        unique=True,
    )

    op.add_column(
        "orders",
        sa.Column("platform_referral_code", sa.String(length=64), nullable=True),
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO referral_programs (
                id, name, description, scope, owner_type, owner_host_id, event_id,
                status, enrollment_mode, starts_at, ends_at, attribution_window_days,
                default_landing_path, hold_period_days, created_by_user_id,
                created_at, updated_at
            )
            SELECT
                gen_random_uuid(),
                c.name,
                c.description,
                'event',
                CASE WHEN c.source = 'platform' THEN 'platform' ELSE 'host' END,
                c.host_id,
                c.event_id,
                CASE
                    WHEN c.status IN ('public_open', 'active') THEN 'active'
                    WHEN c.status = 'paused' THEN 'paused'
                    WHEN c.status IN ('ended', 'archived') THEN c.status
                    ELSE 'active'
                END,
                CASE WHEN c.visibility = 'invite_only' THEN 'invite_only' ELSE 'public_open' END,
                c.starts_at,
                c.ends_at,
                COALESCE(c.cookie_window_days, 30),
                '/events',
                COALESCE(c.hold_period_days, 7),
                c.created_by_user_id,
                c.created_at,
                c.updated_at
            FROM ambassador_campaigns c
            WHERE c.program_id IS NULL
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE ambassador_campaigns c
            SET program_id = p.id
            FROM referral_programs p
            WHERE c.program_id IS NULL
              AND p.event_id IS NOT DISTINCT FROM c.event_id
              AND p.owner_host_id IS NOT DISTINCT FROM c.host_id
              AND p.name = c.name
              AND p.created_at = c.created_at
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE ambassadors a
            SET program_id = c.program_id
            FROM ambassador_campaigns c
            WHERE a.campaign_id = c.id
              AND a.program_id IS NULL
              AND c.program_id IS NOT NULL
            """
        )
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO referral_program_rules (
                id, program_id, product_type, commission_mode, commission_value,
                maximum_commission_per_item, is_active, created_at, updated_at
            )
            SELECT
                gen_random_uuid(),
                c.program_id,
                CASE
                    WHEN c.campaign_type = 'event_merch' OR c.applies_to = 'merch'
                        THEN 'merchandise'
                    ELSE 'ticket'
                END,
                CASE
                    WHEN c.commission_type = 'flat' THEN 'fixed'
                    ELSE 'percentage'
                END,
                COALESCE(c.commission_value, c.commission_percent, 5),
                c.max_commission_per_order,
                true,
                NOW(),
                NOW()
            FROM ambassador_campaigns c
            WHERE c.program_id IS NOT NULL
              AND NOT EXISTS (
                SELECT 1 FROM referral_program_rules r
                WHERE r.program_id = c.program_id
                  AND r.product_type = CASE
                    WHEN c.campaign_type = 'event_merch' OR c.applies_to = 'merch'
                        THEN 'merchandise'
                    ELSE 'ticket'
                  END
              )
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE ambassador_sales
            SET product_slice = 'all',
                idempotency_key = 'legacy:' || order_id::text
            WHERE product_slice = 'all'
              AND idempotency_key IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_column("orders", "platform_referral_code")
    op.drop_index("uq_ambassador_sales_order_slice", table_name="ambassador_sales")
    op.create_unique_constraint(
        "uq_ambassador_sales_order_id", "ambassador_sales", ["order_id"]
    )
    op.drop_index("uq_ambassador_sales_idempotency", table_name="ambassador_sales")
    op.drop_index("ix_ambassador_sales_program_id", table_name="ambassador_sales")
    op.drop_index("ix_ambassador_sales_payer_type", table_name="ambassador_sales")
    op.drop_column("ambassador_sales", "idempotency_key")
    op.drop_column("ambassador_sales", "program_id")
    op.drop_column("ambassador_sales", "product_slice")
    op.drop_column("ambassador_sales", "payer_type")
    op.drop_index("uq_ambassadors_platform_referral", table_name="ambassadors")
    op.alter_column(
        "ambassadors", "host_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False
    )
    op.drop_index("ix_ambassadors_program_id", table_name="ambassadors")
    op.drop_column("ambassadors", "program_id")
    op.drop_index("ix_ambassador_campaigns_program_id", table_name="ambassador_campaigns")
    op.drop_column("ambassador_campaigns", "program_id")
    op.drop_table("referral_program_exclusions")
    op.drop_table("referral_program_rules")
    op.drop_index("ix_referral_programs_owner_host_id", table_name="referral_programs")
    op.drop_index("ix_referral_programs_event_id", table_name="referral_programs")
    op.drop_index("ix_referral_programs_status", table_name="referral_programs")
    op.drop_index("ix_referral_programs_owner_type", table_name="referral_programs")
    op.drop_index("ix_referral_programs_scope", table_name="referral_programs")
    op.drop_table("referral_programs")
