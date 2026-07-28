"""Backfill: paid buyers auto-follow hosts with notifications on.

Revision ID: 20260727_0145
Revises: 20260727_0144
Create Date: 2026-07-27

Product rule: anyone who bought from a host follows that host with
marketing_opt_in=true (host announcement / notify default on). Manual
follows still default marketing_opt_in=false.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260727_0145"
down_revision = "20260727_0144"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Insert missing follows for paid buyers (event-linked).
    op.execute(
        sa.text(
            """
            INSERT INTO host_followers (id, host_id, user_id, marketing_opt_in, created_at)
            SELECT
              gen_random_uuid(),
              e.host_id,
              o.buyer_user_id,
              true,
              NOW()
            FROM orders o
            INNER JOIN events e ON e.id = o.event_id
            INNER JOIN hosts h ON h.id = e.host_id
            WHERE o.status = 'paid'
              AND o.buyer_user_id IS NOT NULL
              AND o.event_id IS NOT NULL
              AND h.user_id IS DISTINCT FROM o.buyer_user_id
              AND NOT EXISTS (
                SELECT 1
                FROM host_followers hf
                WHERE hf.host_id = e.host_id
                  AND hf.user_id = o.buyer_user_id
              )
            GROUP BY e.host_id, o.buyer_user_id
            """
        )
    )
    # Host-shop / merch-only orders with host_id (may already be covered above).
    op.execute(
        sa.text(
            """
            INSERT INTO host_followers (id, host_id, user_id, marketing_opt_in, created_at)
            SELECT
              gen_random_uuid(),
              o.host_id,
              o.buyer_user_id,
              true,
              NOW()
            FROM orders o
            INNER JOIN hosts h ON h.id = o.host_id
            WHERE o.status = 'paid'
              AND o.buyer_user_id IS NOT NULL
              AND o.host_id IS NOT NULL
              AND h.user_id IS DISTINCT FROM o.buyer_user_id
              AND NOT EXISTS (
                SELECT 1
                FROM host_followers hf
                WHERE hf.host_id = o.host_id
                  AND hf.user_id = o.buyer_user_id
              )
            GROUP BY o.host_id, o.buyer_user_id
            """
        )
    )
    # Existing followers who already bought: turn host notifications on.
    op.execute(
        sa.text(
            """
            UPDATE host_followers hf
            SET marketing_opt_in = true
            WHERE hf.marketing_opt_in = false
              AND (
                EXISTS (
                  SELECT 1
                  FROM orders o
                  INNER JOIN events e ON e.id = o.event_id
                  WHERE o.status = 'paid'
                    AND o.buyer_user_id = hf.user_id
                    AND e.host_id = hf.host_id
                )
                OR EXISTS (
                  SELECT 1
                  FROM orders o
                  WHERE o.status = 'paid'
                    AND o.buyer_user_id = hf.user_id
                    AND o.host_id = hf.host_id
                )
              )
            """
        )
    )


def downgrade() -> None:
    # Do not remove follows or flip opt-in back off — irreversible product backfill.
    pass
