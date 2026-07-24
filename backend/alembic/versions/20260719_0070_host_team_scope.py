"""Host team membership scope (host-wide vs selected events).

Revision ID: 20260719_0070
Revises: 20260719_0069
Create Date: 2026-07-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260719_0070"
down_revision = "20260719_0069"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "host_team_members",
        sa.Column(
            "scope",
            sa.String(length=32),
            nullable=False,
            server_default="host_wide",
        ),
    )
    op.add_column(
        "host_team_members",
        sa.Column(
            "scoped_event_ids_json",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    # Desk roles default to selected_events; others stay host_wide.
    op.execute(
        """
        UPDATE host_team_members
        SET scope = 'selected_events'
        WHERE lower(role) IN ('scanner', 'merch_staff', 'viewer')
        """
    )
    op.alter_column("host_team_members", "scope", server_default=None)
    op.alter_column(
        "host_team_members", "scoped_event_ids_json", server_default=None
    )


def downgrade() -> None:
    op.drop_column("host_team_members", "scoped_event_ids_json")
    op.drop_column("host_team_members", "scope")
