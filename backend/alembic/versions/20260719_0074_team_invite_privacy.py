"""Store invitee kind/username; hide email for username invites.

Revision ID: 20260719_0074
Revises: 20260719_0073
Create Date: 2026-07-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260719_0074"
down_revision = "20260719_0073"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "host_team_invites",
        sa.Column(
            "invitee_kind",
            sa.String(length=16),
            nullable=False,
            server_default="email",
        ),
    )
    op.add_column(
        "host_team_invites",
        sa.Column("invited_username", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "host_team_members",
        sa.Column(
            "invitee_kind",
            sa.String(length=16),
            nullable=False,
            server_default="email",
        ),
    )
    op.add_column(
        "host_team_members",
        sa.Column("invited_username", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("host_team_members", "invited_username")
    op.drop_column("host_team_members", "invitee_kind")
    op.drop_column("host_team_invites", "invited_username")
    op.drop_column("host_team_invites", "invitee_kind")
