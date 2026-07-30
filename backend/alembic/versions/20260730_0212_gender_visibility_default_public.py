"""Default gender visibility to public (everyone) unless the user changes it.

Revision ID: 20260730_0212
Revises: 20260730_0211
Create Date: 2026-07-30

Existing rows still on the old connections_only default are migrated to public.
Users who chose private stay private.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260730_0212"
down_revision = "20260730_0211"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE users SET gender_visibility = 'public' "
            "WHERE gender_visibility = 'connections_only'"
        )
    )
    op.alter_column(
        "users",
        "gender_visibility",
        server_default="public",
        existing_type=sa.String(length=32),
        existing_nullable=False,
    )
    # Drop stale public directory/host cards that still hide gender.
    try:
        from app.core.cache_invalidation import (
            invalidate_fan_public_caches,
            invalidate_host_public_caches,
        )

        invalidate_fan_public_caches()
        invalidate_host_public_caches()
    except Exception:
        # Migration must not fail if Redis/cache is unavailable.
        pass


def downgrade() -> None:
    op.alter_column(
        "users",
        "gender_visibility",
        server_default="connections_only",
        existing_type=sa.String(length=32),
        existing_nullable=False,
    )
