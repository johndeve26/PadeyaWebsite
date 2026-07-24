"""Fan Passport directory opt-in + admin hide.

Revision ID: 20260718_0039
Revises: 20260718_0038
Create Date: 2026-07-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260718_0039"
down_revision = "20260718_0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "fan_passports",
        sa.Column(
            "appear_in_directory",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "fan_passports",
        sa.Column("admin_hidden_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "fan_passports",
        sa.Column("admin_hidden_reason", sa.String(length=500), nullable=True),
    )
    op.create_index(
        "ix_fan_passports_appear_in_directory",
        "fan_passports",
        ["appear_in_directory"],
        unique=False,
    )
    op.create_index(
        "ix_fan_passports_directory_list",
        "fan_passports",
        ["visibility", "appear_in_directory"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_fan_passports_directory_list", table_name="fan_passports")
    op.drop_index("ix_fan_passports_appear_in_directory", table_name="fan_passports")
    op.drop_column("fan_passports", "admin_hidden_reason")
    op.drop_column("fan_passports", "admin_hidden_at")
    op.drop_column("fan_passports", "appear_in_directory")
