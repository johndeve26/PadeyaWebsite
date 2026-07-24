"""Evolve user_admin_flags to MVP catalog fields.

Revision ID: 20260720_0093
Revises: 20260720_0092
Create Date: 2026-07-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260720_0093"
down_revision = "20260720_0092"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE user_admin_flags SET status = 'active' WHERE status = 'open'"
        )
    )

    with op.batch_alter_table("user_admin_flags") as batch:
        batch.alter_column("code", new_column_name="flag_type")
        batch.alter_column(
            "created_by_user_id", new_column_name="created_by_admin_id"
        )
        batch.alter_column(
            "resolved_by_user_id", new_column_name="resolved_by_admin_id"
        )
        batch.add_column(
            sa.Column(
                "severity",
                sa.String(length=16),
                nullable=False,
                server_default="medium",
            )
        )
        batch.add_column(sa.Column("internal_note", sa.Text(), nullable=True))
        batch.create_index(
            "ix_user_admin_flags_flag_type", ["flag_type"], unique=False
        )
        batch.create_index(
            "ix_user_admin_flags_severity", ["severity"], unique=False
        )

    op.alter_column("user_admin_flags", "severity", server_default=None)


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE user_admin_flags SET status = 'open' WHERE status = 'active'"
        )
    )

    with op.batch_alter_table("user_admin_flags") as batch:
        batch.drop_index("ix_user_admin_flags_severity")
        batch.drop_index("ix_user_admin_flags_flag_type")
        batch.drop_column("internal_note")
        batch.drop_column("severity")
        batch.alter_column(
            "resolved_by_admin_id", new_column_name="resolved_by_user_id"
        )
        batch.alter_column(
            "created_by_admin_id", new_column_name="created_by_user_id"
        )
        batch.alter_column("flag_type", new_column_name="code")
