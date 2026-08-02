"""Migrate pending_review events to published + soft flag.

Revision ID: 20260802_0214
Revises: 20260730_0213
Create Date: 2026-08-02

Publish-first: hosts are never gated on pending_review. Existing rows
become published and flagged for admin review later.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260802_0214"
down_revision = "20260730_0213"
branch_labels = None
depends_on = None

_MIGRATION_REASON = "Migrated from pending_review"


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE events
            SET
                status = 'published',
                published_at = COALESCE(published_at, NOW()),
                admin_flagged_at = COALESCE(admin_flagged_at, NOW()),
                admin_flag_reason = COALESCE(admin_flag_reason, :reason)
            WHERE status = 'pending_review'
            """
        ),
        {"reason": _MIGRATION_REASON},
    )


def downgrade() -> None:
    # Best-effort: restore rows that still carry the migration flag reason.
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE events
            SET status = 'pending_review', published_at = NULL
            WHERE status = 'published'
              AND admin_flag_reason = :reason
            """
        ),
        {"reason": _MIGRATION_REASON},
    )
