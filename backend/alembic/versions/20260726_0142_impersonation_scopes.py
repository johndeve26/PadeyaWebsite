"""Add scopes JSON to admin impersonation sessions.

Revision ID: 20260726_0142
Revises: 20260724_0141
Create Date: 2026-07-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260726_0142"
down_revision = "20260724_0141"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "admin_impersonation_sessions",
        sa.Column(
            "scopes",
            sa.JSON()
            .with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default=sa.text("'[\"view\"]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("admin_impersonation_sessions", "scopes")
