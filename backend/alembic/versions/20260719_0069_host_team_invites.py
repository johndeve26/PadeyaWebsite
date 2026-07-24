"""Host team pending invites, permissions, and lifecycle fields.

Revision ID: 20260719_0069
Revises: 20260719_0068
Create Date: 2026-07-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260719_0069"
down_revision = "20260719_0068"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_host_team_members_host_user", "host_team_members", type_="unique"
    )
    op.alter_column(
        "host_team_members",
        "user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.add_column(
        "host_team_members",
        sa.Column("role", sa.String(length=32), nullable=False, server_default="scanner"),
    )
    op.add_column(
        "host_team_members",
        sa.Column(
            "permissions_json",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default=sa.text(
                "'{\"scan_tickets\": true, \"scan_merch\": true, "
                "\"view_attendees\": false, \"manage_event_staff\": false}'::jsonb"
            ),
        ),
    )
    op.add_column(
        "host_team_members",
        sa.Column("invite_token_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "host_team_members",
        sa.Column("invite_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "host_team_members",
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "host_team_members",
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "host_team_members",
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_host_team_members_invite_token_hash",
        "host_team_members",
        ["invite_token_hash"],
        unique=False,
    )
    # One accepted/active membership per user per host
    op.execute(
        """
        CREATE UNIQUE INDEX uq_host_team_members_host_user_active
        ON host_team_members (host_id, user_id)
        WHERE user_id IS NOT NULL AND archived_at IS NULL
          AND status IN ('active', 'suspended', 'pending')
        """
    )
    # One open pending invite per email per host
    op.execute(
        """
        CREATE UNIQUE INDEX uq_host_team_members_host_pending_email
        ON host_team_members (host_id, lower(invited_email))
        WHERE status = 'pending'
          AND archived_at IS NULL
          AND invited_email IS NOT NULL
        """
    )
    # Backfill role from role_label for existing rows
    op.execute(
        """
        UPDATE host_team_members
        SET role = CASE
            WHEN lower(role_label) IN ('manager', 'co_host', 'co-host') THEN 'manager'
            WHEN lower(role_label) IN ('ops', 'operations', 'staff') THEN 'ops'
            ELSE 'scanner'
        END,
        permissions_json = CASE
            WHEN lower(role_label) IN ('manager', 'co_host', 'co-host') THEN
              '{"scan_tickets": true, "scan_merch": true, "view_attendees": true, "manage_event_staff": true}'::jsonb
            WHEN lower(role_label) IN ('ops', 'operations', 'staff') THEN
              '{"scan_tickets": true, "scan_merch": true, "view_attendees": true, "manage_event_staff": false}'::jsonb
            ELSE
              '{"scan_tickets": true, "scan_merch": true, "view_attendees": false, "manage_event_staff": false}'::jsonb
        END,
        accepted_at = COALESCE(accepted_at, created_at)
        WHERE user_id IS NOT NULL AND status = 'active'
        """
    )
    op.alter_column("host_team_members", "role", server_default=None)
    op.alter_column("host_team_members", "permissions_json", server_default=None)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_host_team_members_host_pending_email")
    op.execute("DROP INDEX IF EXISTS uq_host_team_members_host_user_active")
    op.drop_index("ix_host_team_members_invite_token_hash", table_name="host_team_members")
    op.drop_column("host_team_members", "suspended_at")
    op.drop_column("host_team_members", "accepted_at")
    op.drop_column("host_team_members", "invited_at")
    op.drop_column("host_team_members", "invite_expires_at")
    op.drop_column("host_team_members", "invite_token_hash")
    op.drop_column("host_team_members", "permissions_json")
    op.drop_column("host_team_members", "role")
    op.execute("DELETE FROM host_team_members WHERE user_id IS NULL")
    op.alter_column(
        "host_team_members",
        "user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.create_unique_constraint(
        "uq_host_team_members_host_user",
        "host_team_members",
        ["host_id", "user_id"],
    )
