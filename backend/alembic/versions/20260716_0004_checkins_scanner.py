"""checkins scanner sessions staff assignments

Revision ID: 20260716_0004
Revises: 20260716_0003
Create Date: 2026-07-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260716_0004"
down_revision: Union[str, Sequence[str], None] = "20260716_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "event_staff_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("role_label", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "user_id", name="uq_event_staff_assignments"),
    )
    op.create_index(
        "ix_event_staff_assignments_event_id",
        "event_staff_assignments",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        "ix_event_staff_assignments_user_id",
        "event_staff_assignments",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "scanner_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("device_label", sa.String(length=120), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scanner_sessions_event_id", "scanner_sessions", ["event_id"], unique=False)
    op.create_index("ix_scanner_sessions_user_id", "scanner_sessions", ["user_id"], unique=False)
    op.create_index("ix_scanner_sessions_status", "scanner_sessions", ["status"], unique=False)

    op.create_table(
        "checkins",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=True),
        sa.Column("ticket_public_code", sa.String(length=40), nullable=True),
        sa.Column("scanner_session_id", sa.Uuid(), nullable=True),
        sa.Column("scanned_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("method", sa.String(length=32), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("holder_name", sa.String(length=200), nullable=True),
        sa.Column("ticket_type_name", sa.String(length=160), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["scanner_session_id"], ["scanner_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["scanned_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_checkins_event_id", "checkins", ["event_id"], unique=False)
    op.create_index("ix_checkins_ticket_id", "checkins", ["ticket_id"], unique=False)
    op.create_index("ix_checkins_ticket_public_code", "checkins", ["ticket_public_code"], unique=False)
    op.create_index("ix_checkins_scanner_session_id", "checkins", ["scanner_session_id"], unique=False)
    op.create_index("ix_checkins_scanned_by_user_id", "checkins", ["scanned_by_user_id"], unique=False)
    op.create_index("ix_checkins_outcome", "checkins", ["outcome"], unique=False)
    op.create_index("ix_checkins_created_at", "checkins", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_checkins_created_at", table_name="checkins")
    op.drop_index("ix_checkins_outcome", table_name="checkins")
    op.drop_index("ix_checkins_scanned_by_user_id", table_name="checkins")
    op.drop_index("ix_checkins_scanner_session_id", table_name="checkins")
    op.drop_index("ix_checkins_ticket_public_code", table_name="checkins")
    op.drop_index("ix_checkins_ticket_id", table_name="checkins")
    op.drop_index("ix_checkins_event_id", table_name="checkins")
    op.drop_table("checkins")
    op.drop_index("ix_scanner_sessions_status", table_name="scanner_sessions")
    op.drop_index("ix_scanner_sessions_user_id", table_name="scanner_sessions")
    op.drop_index("ix_scanner_sessions_event_id", table_name="scanner_sessions")
    op.drop_table("scanner_sessions")
    op.drop_index("ix_event_staff_assignments_user_id", table_name="event_staff_assignments")
    op.drop_index("ix_event_staff_assignments_event_id", table_name="event_staff_assignments")
    op.drop_table("event_staff_assignments")
    op.drop_column("tickets", "checked_in_at")
