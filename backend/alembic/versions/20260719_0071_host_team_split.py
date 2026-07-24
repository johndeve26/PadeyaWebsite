"""Split host team invites/members/audit; extend event staff.

Revision ID: 20260719_0071
Revises: 20260719_0070
Create Date: 2026-07-19

``host_id`` on these tables is the host workspace id (product: host profile id).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260719_0071"
down_revision = "20260719_0070"
branch_labels = None
depends_on = None

JSON_VARIANT = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "host_team_invites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("role_label", sa.String(length=64), nullable=False),
        sa.Column("permissions_json", JSON_VARIANT, nullable=False),
        sa.Column("scope_json", JSON_VARIANT, nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("invited_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("invited_user_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["invited_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_host_team_invites_host_id", "host_team_invites", ["host_id"])
    op.create_index("ix_host_team_invites_email", "host_team_invites", ["email"])
    op.create_index("ix_host_team_invites_token_hash", "host_team_invites", ["token_hash"])
    op.create_index("ix_host_team_invites_status", "host_team_invites", ["status"])
    op.execute(
        """
        CREATE UNIQUE INDEX uq_host_team_invites_host_pending_email
        ON host_team_invites (host_id, lower(email))
        WHERE status = 'pending'
        """
    )

    op.create_table(
        "host_team_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("target_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", JSON_VARIANT, nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_host_team_audit_logs_host_id", "host_team_audit_logs", ["host_id"])
    op.create_index("ix_host_team_audit_logs_action", "host_team_audit_logs", ["action"])
    op.create_index(
        "ix_host_team_audit_logs_created_at", "host_team_audit_logs", ["created_at"]
    )

    # Move open / closed invite rows off the unified members table.
    op.execute(
        """
        INSERT INTO host_team_invites (
            id, host_id, email, role, role_label, permissions_json, scope_json,
            token_hash, status, invited_by_user_id, invited_user_id,
            expires_at, accepted_at, revoked_at, created_at, updated_at
        )
        SELECT
            id,
            host_id,
            lower(coalesce(invited_email, '')),
            coalesce(role, 'scanner'),
            coalesce(role_label, 'scanner'),
            coalesce(permissions_json, '{}'::jsonb),
            jsonb_build_object(
                'type', coalesce(nullif(scope, ''), 'host_wide'),
                'event_ids', coalesce(scoped_event_ids_json, '[]'::jsonb)
            ),
            coalesce(invite_token_hash, ''),
            CASE
                WHEN status = 'declined' THEN 'revoked'
                WHEN status = 'expired' THEN 'expired'
                WHEN status = 'pending' THEN 'pending'
                ELSE 'revoked'
            END,
            created_by,
            user_id,
            invite_expires_at,
            NULL,
            CASE WHEN status = 'declined' THEN updated_at ELSE NULL END,
            created_at,
            updated_at
        FROM host_team_members
        WHERE status IN ('pending', 'declined', 'expired')
          AND invited_email IS NOT NULL
          AND length(trim(invited_email)) > 0
        """
    )
    op.execute(
        """
        DELETE FROM host_team_members
        WHERE status IN ('pending', 'declined', 'expired')
        """
    )

    op.add_column(
        "host_team_members",
        sa.Column(
            "scope_json",
            JSON_VARIANT,
            nullable=False,
            server_default=sa.text("'{\"type\":\"host_wide\",\"event_ids\":[]}'::jsonb"),
        ),
    )
    op.add_column(
        "host_team_members",
        sa.Column("invited_by_user_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "host_team_members",
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "host_team_members",
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_host_team_members_invited_by_user_id",
        "host_team_members",
        "users",
        ["invited_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.execute(
        """
        UPDATE host_team_members
        SET scope_json = jsonb_build_object(
                'type', coalesce(nullif(scope, ''), 'host_wide'),
                'event_ids', coalesce(scoped_event_ids_json, '[]'::jsonb)
            ),
            invited_by_user_id = created_by,
            joined_at = coalesce(accepted_at, created_at),
            removed_at = archived_at,
            status = CASE
                WHEN archived_at IS NOT NULL OR status = 'archived' THEN 'removed'
                WHEN status = 'inactive' THEN 'suspended'
                WHEN status = 'invited' THEN 'active'
                ELSE status
            END
        """
    )

    # Drop invite-era partial uniques / indexes before reshaping.
    op.execute("DROP INDEX IF EXISTS uq_host_team_members_host_pending_email")
    op.execute("DROP INDEX IF EXISTS uq_host_team_members_host_user_active")
    op.drop_index("ix_host_team_members_invite_token_hash", table_name="host_team_members")

    op.execute("DELETE FROM host_team_members WHERE user_id IS NULL")
    op.alter_column(
        "host_team_members",
        "user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    # One live membership per user per host (removed rows may remain for history).
    op.execute(
        """
        CREATE UNIQUE INDEX uq_host_team_members_host_user_live
        ON host_team_members (host_id, user_id)
        WHERE status IN ('active', 'suspended', 'invited')
          AND removed_at IS NULL
        """
    )

    op.drop_column("host_team_members", "invite_token_hash")
    op.drop_column("host_team_members", "invite_expires_at")
    op.drop_column("host_team_members", "invited_at")
    op.drop_column("host_team_members", "accepted_at")
    op.drop_column("host_team_members", "invited_email")
    op.drop_column("host_team_members", "scope")
    op.drop_column("host_team_members", "scoped_event_ids_json")
    op.drop_column("host_team_members", "archived_at")
    op.drop_column("host_team_members", "archived_by")
    op.drop_column("host_team_members", "created_by")
    op.drop_column("host_team_members", "updated_by")

    op.alter_column("host_team_members", "scope_json", server_default=None)

    # Extend event_staff_assignments for team linkage and typed desk roles.
    op.add_column(
        "event_staff_assignments",
        sa.Column("team_member_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "event_staff_assignments",
        sa.Column(
            "assignment_type",
            sa.String(length=32),
            nullable=False,
            server_default="ticket_scanner",
        ),
    )
    op.add_column(
        "event_staff_assignments",
        sa.Column("permissions_json", JSON_VARIANT, nullable=True),
    )
    op.add_column(
        "event_staff_assignments",
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="active",
        ),
    )
    op.add_column(
        "event_staff_assignments",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_event_staff_assignments_team_member_id",
        "event_staff_assignments",
        ["team_member_id"],
    )
    op.create_index(
        "ix_event_staff_assignments_status",
        "event_staff_assignments",
        ["status"],
    )
    op.create_foreign_key(
        "fk_event_staff_assignments_team_member_id",
        "event_staff_assignments",
        "host_team_members",
        ["team_member_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        """
        UPDATE event_staff_assignments
        SET assignment_type = CASE
            WHEN lower(role_label) LIKE '%merch%' THEN 'merch_pickup'
            WHEN lower(role_label) IN ('ops', 'operations', 'event_ops', 'manager')
                THEN 'event_ops'
            ELSE 'ticket_scanner'
        END
        """
    )
    op.alter_column("event_staff_assignments", "assignment_type", server_default=None)
    op.alter_column("event_staff_assignments", "status", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "fk_event_staff_assignments_team_member_id",
        "event_staff_assignments",
        type_="foreignkey",
    )
    op.drop_index("ix_event_staff_assignments_status", table_name="event_staff_assignments")
    op.drop_index(
        "ix_event_staff_assignments_team_member_id", table_name="event_staff_assignments"
    )
    op.drop_column("event_staff_assignments", "expires_at")
    op.drop_column("event_staff_assignments", "status")
    op.drop_column("event_staff_assignments", "permissions_json")
    op.drop_column("event_staff_assignments", "assignment_type")
    op.drop_column("event_staff_assignments", "team_member_id")

    op.add_column(
        "host_team_members",
        sa.Column("updated_by", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "host_team_members",
        sa.Column("created_by", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "host_team_members",
        sa.Column("archived_by", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "host_team_members",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "host_team_members",
        sa.Column("scoped_event_ids_json", JSON_VARIANT, nullable=True),
    )
    op.add_column(
        "host_team_members",
        sa.Column("scope", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "host_team_members",
        sa.Column("invited_email", sa.String(length=320), nullable=True),
    )
    op.add_column(
        "host_team_members",
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "host_team_members",
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "host_team_members",
        sa.Column("invite_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "host_team_members",
        sa.Column("invite_token_hash", sa.String(length=64), nullable=True),
    )

    op.execute(
        """
        UPDATE host_team_members
        SET scope = coalesce(scope_json->>'type', 'host_wide'),
            scoped_event_ids_json = coalesce(scope_json->'event_ids', '[]'::jsonb),
            created_by = invited_by_user_id,
            accepted_at = joined_at,
            archived_at = removed_at,
            status = CASE WHEN status = 'removed' THEN 'archived' ELSE status END
        """
    )
    op.execute(
        """
        INSERT INTO host_team_members (
            id, host_id, user_id, role, role_label, status, invited_email,
            permissions_json, scope, scoped_event_ids_json, invite_token_hash,
            invite_expires_at, invited_at, accepted_at, suspended_at,
            created_by, updated_by, archived_at, created_at, updated_at
        )
        SELECT
            id, host_id, invited_user_id, role, role_label,
            CASE
                WHEN status = 'revoked' THEN 'declined'
                ELSE status
            END,
            email, permissions_json,
            coalesce(scope_json->>'type', 'host_wide'),
            coalesce(scope_json->'event_ids', '[]'::jsonb),
            nullif(token_hash, ''),
            expires_at, created_at, accepted_at, NULL,
            invited_by_user_id, invited_by_user_id, NULL, created_at, updated_at
        FROM host_team_invites
        WHERE status IN ('pending', 'expired', 'revoked')
        """
    )

    op.execute("DROP INDEX IF EXISTS uq_host_team_members_host_user_live")
    op.alter_column(
        "host_team_members",
        "user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.drop_constraint(
        "fk_host_team_members_invited_by_user_id",
        "host_team_members",
        type_="foreignkey",
    )
    op.drop_column("host_team_members", "removed_at")
    op.drop_column("host_team_members", "joined_at")
    op.drop_column("host_team_members", "invited_by_user_id")
    op.drop_column("host_team_members", "scope_json")

    op.execute("DROP INDEX IF EXISTS uq_host_team_invites_host_pending_email")
    op.drop_table("host_team_audit_logs")
    op.drop_table("host_team_invites")

    op.execute(
        """
        CREATE UNIQUE INDEX uq_host_team_members_host_user_active
        ON host_team_members (host_id, user_id)
        WHERE user_id IS NOT NULL AND archived_at IS NULL
          AND status IN ('active', 'suspended', 'pending')
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_host_team_members_host_pending_email
        ON host_team_members (host_id, lower(invited_email))
        WHERE status = 'pending'
          AND archived_at IS NULL
          AND invited_email IS NOT NULL
        """
    )
    op.create_index(
        "ix_host_team_members_invite_token_hash",
        "host_team_members",
        ["invite_token_hash"],
    )
