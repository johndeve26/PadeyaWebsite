"""Add privacy-aware gender fields on users.

Revision ID: 20260729_0148
Revises: 20260729_0147
Create Date: 2026-07-29

Nullable gender for existing users; non-null visibility default connections_only.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260729_0148"
down_revision = "20260729_0147"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("gender", sa.String(length=32), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "gender_visibility",
            sa.String(length=32),
            nullable=False,
            server_default="connections_only",
        ),
    )
    op.create_check_constraint(
        "ck_users_gender",
        "users",
        "gender IS NULL OR gender IN ('male', 'female', 'prefer_not_to_say')",
    )
    op.create_check_constraint(
        "ck_users_gender_visibility",
        "users",
        "gender_visibility IN ('public', 'connections_only', 'private')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_gender_visibility", "users", type_="check")
    op.drop_constraint("ck_users_gender", "users", type_="check")
    op.drop_column("users", "gender_visibility")
    op.drop_column("users", "gender")
