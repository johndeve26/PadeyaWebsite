"""Rename invitee_kind → invite_method on team invites/members.

Revision ID: 20260719_0075
Revises: 20260719_0074
Create Date: 2026-07-19

``host_team_invites`` fields:
- invite_method: email | username
- invited_username (nullable)
- invited_user_id (nullable, already present)
- email: kept populated for outbox delivery (not exposed for username invites)
- token_hash, expires_at, status (pending/accepted/expired/revoked) unchanged
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260719_0075"
down_revision = "20260719_0074"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "host_team_invites",
        "invitee_kind",
        new_column_name="invite_method",
        existing_type=sa.String(length=16),
        existing_nullable=False,
        existing_server_default="email",
    )
    op.alter_column(
        "host_team_members",
        "invitee_kind",
        new_column_name="invite_method",
        existing_type=sa.String(length=16),
        existing_nullable=False,
        existing_server_default="email",
    )


def downgrade() -> None:
    op.alter_column(
        "host_team_members",
        "invite_method",
        new_column_name="invitee_kind",
        existing_type=sa.String(length=16),
        existing_nullable=False,
        existing_server_default="email",
    )
    op.alter_column(
        "host_team_invites",
        "invite_method",
        new_column_name="invitee_kind",
        existing_type=sa.String(length=16),
        existing_nullable=False,
        existing_server_default="email",
    )
