"""Item-level referral attributions and append-only commission ledger.

Revision ID: 20260803_0216
Revises: 20260803_0215
Create Date: 2026-08-03

Backfills ledger earnings from ambassador_sales without recalculating amounts.
Writes migration audit to docs/artifacts (counts only, no PII).
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260803_0216"
down_revision = "20260803_0215"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "referral_attributions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "order_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("order_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("attribution_item_key", sa.String(length=120), nullable=False),
        sa.Column(
            "program_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("referral_programs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "campaign_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ambassador_campaigns.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "enrollment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ambassadors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "ambassador_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "host_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hosts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("product_type", sa.String(length=32), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payer_type", sa.String(length=32), nullable=False),
        sa.Column("winning_scope", sa.String(length=32), nullable=False),
        sa.Column("attribution_source", sa.String(length=32), nullable=True),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column(
            "resolved_at",
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
        sa.UniqueConstraint(
            "order_id",
            "attribution_item_key",
            name="uq_referral_attributions_order_item",
        ),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_referral_attributions_idempotency"
        ),
    )
    op.create_index(
        "ix_referral_attributions_order_id", "referral_attributions", ["order_id"]
    )
    op.create_index(
        "ix_referral_attributions_enrollment_id",
        "referral_attributions",
        ["enrollment_id"],
    )
    op.create_index(
        "ix_referral_attributions_payer_type", "referral_attributions", ["payer_type"]
    )

    op.create_table(
        "referral_commission_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "attribution_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("referral_attributions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "program_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("referral_programs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "campaign_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ambassador_campaigns.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "rule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("referral_program_rules.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "enrollment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ambassadors.id", ondelete="SET NULL"),
            nullable=False,
        ),
        sa.Column(
            "ambassador_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "order_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("order_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("attribution_item_key", sa.String(length=120), nullable=False),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "host_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hosts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("product_type", sa.String(length=32), nullable=False),
        sa.Column("payer_type", sa.String(length=32), nullable=False),
        sa.Column("entry_type", sa.String(length=32), nullable=False),
        sa.Column(
            "original_entry_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("referral_commission_entries.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "gross_item_amount",
            sa.Numeric(14, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "eligible_commission_base",
            sa.Numeric(14, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column("commission_mode", sa.String(length=32), nullable=False),
        sa.Column(
            "commission_rate", sa.Numeric(12, 4), nullable=False, server_default="0"
        ),
        sa.Column("commission_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="NGN"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("source_event_id", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payable_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_referral_commission_entries_idempotency"
        ),
    )
    op.create_index(
        "ix_referral_commission_entries_order_id",
        "referral_commission_entries",
        ["order_id"],
    )
    op.create_index(
        "ix_referral_commission_entries_enrollment_id",
        "referral_commission_entries",
        ["enrollment_id"],
    )
    op.create_index(
        "ix_referral_commission_entries_payer_type",
        "referral_commission_entries",
        ["payer_type"],
    )
    op.create_index(
        "ix_referral_commission_entries_entry_type",
        "referral_commission_entries",
        ["entry_type"],
    )
    op.create_index(
        "ix_referral_commission_entries_ambassador_created",
        "referral_commission_entries",
        ["ambassador_user_id", "created_at"],
    )
    op.create_index(
        "ix_referral_commission_entries_payer_status",
        "referral_commission_entries",
        ["payer_type", "status"],
    )

    op.drop_index("uq_ambassador_sales_order_slice", table_name="ambassador_sales")
    op.create_index(
        "uq_ambassador_sales_order_slice_amb",
        "ambassador_sales",
        ["order_id", "product_slice", "ambassador_id"],
        unique=True,
    )

    conn = op.get_bind()
    sales_count = conn.execute(sa.text("SELECT COUNT(*) FROM ambassador_sales")).scalar()
    sales_count = int(sales_count or 0)

    # Backfill: one synthetic attribution + earning per legacy sale (preserve amounts)
    conn.execute(
        sa.text(
            """
            INSERT INTO referral_attributions (
                id, order_id, order_item_id, attribution_item_key, program_id, campaign_id,
                enrollment_id, ambassador_user_id, event_id, host_id, product_type,
                product_id, payer_type, winning_scope, attribution_source,
                idempotency_key, resolved_at, created_at
            )
            SELECT
                gen_random_uuid(),
                s.order_id,
                NULL,
                'legacy-sale:' || s.id::text,
                s.program_id,
                a.campaign_id,
                s.ambassador_id,
                a.user_id,
                s.event_id,
                a.host_id,
                CASE
                    WHEN s.product_slice = 'merch' THEN 'merchandise'
                    WHEN s.product_slice = 'tickets' THEN 'ticket'
                    WHEN COALESCE(s.merch_units_sold, 0) > 0
                         AND COALESCE(s.tickets_sold, 0) = 0 THEN 'merchandise'
                    ELSE 'ticket'
                END,
                NULL,
                COALESCE(NULLIF(s.payer_type, ''), 'host'),
                CASE
                    WHEN a.program_kind = 'platform_wide' THEN 'platform'
                    ELSE 'event'
                END,
                'legacy',
                'legacy-attr:' || s.id::text,
                s.created_at,
                s.created_at
            FROM ambassador_sales s
            JOIN ambassadors a ON a.id = s.ambassador_id
            WHERE NOT EXISTS (
                SELECT 1 FROM referral_attributions ra
                WHERE ra.idempotency_key = 'legacy-attr:' || s.id::text
            )
            """
        )
    )

    conn.execute(
        sa.text(
            """
            INSERT INTO referral_commission_entries (
                id, attribution_id, program_id, campaign_id, rule_id, enrollment_id,
                ambassador_user_id, order_id, order_item_id, attribution_item_key,
                event_id, host_id, product_type, payer_type, entry_type,
                original_entry_id, gross_item_amount, eligible_commission_base,
                commission_mode, commission_rate, commission_amount, currency,
                status, idempotency_key, source_event_id, notes, created_at,
                approved_at, payable_at, paid_at
            )
            SELECT
                gen_random_uuid(),
                ra.id,
                ra.program_id,
                ra.campaign_id,
                NULL,
                s.ambassador_id,
                ra.ambassador_user_id,
                s.order_id,
                NULL,
                ra.attribution_item_key,
                s.event_id,
                ra.host_id,
                ra.product_type,
                COALESCE(NULLIF(s.payer_type, ''), 'host'),
                'earning',
                NULL,
                COALESCE(s.revenue_amount, 0),
                COALESCE(s.revenue_amount, 0),
                COALESCE(NULLIF(s.commission_type, ''), 'percentage'),
                CASE
                    WHEN COALESCE(s.revenue_amount, 0) > 0
                    THEN ROUND(
                        (COALESCE(s.commission_owed, 0) / NULLIF(s.revenue_amount, 0)) * 100,
                        4
                    )
                    ELSE 0
                END,
                COALESCE(s.commission_owed, 0),
                'NGN',
                CASE
                    WHEN s.status = 'paid' THEN 'paid'
                    WHEN s.status = 'approved' THEN 'approved'
                    WHEN s.status = 'reversed' THEN 'paid'
                    ELSE 'pending'
                END,
                'referral-earning-legacy:' || s.id::text,
                'backfill:ambassador_sales',
                'Backfilled from ambassador_sales; amount preserved',
                s.created_at,
                CASE WHEN s.status IN ('approved', 'paid') THEN s.created_at ELSE NULL END,
                CASE WHEN s.status IN ('approved', 'paid') THEN s.hold_until ELSE NULL END,
                CASE WHEN s.status = 'paid' THEN COALESCE(s.reward_status_updated_at, s.created_at) ELSE NULL END
            FROM ambassador_sales s
            JOIN referral_attributions ra
              ON ra.idempotency_key = 'legacy-attr:' || s.id::text
            WHERE NOT EXISTS (
                SELECT 1 FROM referral_commission_entries e
                WHERE e.idempotency_key = 'referral-earning-legacy:' || s.id::text
            )
            """
        )
    )

    # Append reversals for already-reversed sales (preserve original earning)
    conn.execute(
        sa.text(
            """
            INSERT INTO referral_commission_entries (
                id, attribution_id, program_id, campaign_id, rule_id, enrollment_id,
                ambassador_user_id, order_id, order_item_id, attribution_item_key,
                event_id, host_id, product_type, payer_type, entry_type,
                original_entry_id, gross_item_amount, eligible_commission_base,
                commission_mode, commission_rate, commission_amount, currency,
                status, idempotency_key, source_event_id, notes, created_at
            )
            SELECT
                gen_random_uuid(),
                e.attribution_id,
                e.program_id,
                e.campaign_id,
                NULL,
                e.enrollment_id,
                e.ambassador_user_id,
                e.order_id,
                NULL,
                e.attribution_item_key,
                e.event_id,
                e.host_id,
                e.product_type,
                e.payer_type,
                'reversal',
                e.id,
                e.gross_item_amount,
                e.eligible_commission_base,
                e.commission_mode,
                e.commission_rate,
                -ABS(e.commission_amount),
                e.currency,
                'paid',
                'referral-reversal-legacy:' || s.id::text,
                'backfill:ambassador_sales_reversed',
                COALESCE(s.reversal_reason, 'Legacy sale reversed'),
                COALESCE(s.reversed_at, s.created_at)
            FROM ambassador_sales s
            JOIN referral_commission_entries e
              ON e.idempotency_key = 'referral-earning-legacy:' || s.id::text
            WHERE s.status = 'reversed'
              AND NOT EXISTS (
                SELECT 1 FROM referral_commission_entries r
                WHERE r.idempotency_key = 'referral-reversal-legacy:' || s.id::text
              )
            """
        )
    )

    backfilled = conn.execute(
        sa.text(
            """
            SELECT COUNT(*) FROM referral_commission_entries
            WHERE source_event_id LIKE 'backfill:%'
            """
        )
    ).scalar()
    backfilled = int(backfilled or 0)

    host_entries = conn.execute(
        sa.text(
            "SELECT COUNT(*) FROM referral_commission_entries WHERE payer_type = 'host'"
        )
    ).scalar()
    platform_entries = conn.execute(
        sa.text(
            "SELECT COUNT(*) FROM referral_commission_entries WHERE payer_type = 'platform'"
        )
    ).scalar()

    artifact = {
        "migration": "20260803_0216",
        "existing_sales_count": sales_count,
        "entries_backfilled": backfilled,
        "unmapped_rows": max(0, sales_count - int(
            conn.execute(
                sa.text(
                    """
                    SELECT COUNT(*) FROM referral_commission_entries
                    WHERE idempotency_key LIKE 'referral-earning-legacy:%'
                    """
                )
            ).scalar()
            or 0
        )),
        "duplicate_rows_prevented": True,
        "host_payer_entries": int(host_entries or 0),
        "platform_payer_entries": int(platform_entries or 0),
        "notes": "Amounts preserved from ambassador_sales; no recalculation.",
    }
    # Best-effort artifact under repo docs (may be absent in some deploy images)
    try:
        root = Path(__file__).resolve().parents[3]
        out_dir = root / "docs" / "artifacts"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "referral_ledger_backfill_20260803_0216.json").write_text(
            json.dumps(artifact, indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception:
        pass


def downgrade() -> None:
    op.drop_table("referral_commission_entries")
    op.drop_table("referral_attributions")
