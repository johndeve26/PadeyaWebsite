"""Fan Connect directional decline cooldown fields."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260722_0129"
down_revision = "20260722_0128"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "fan_connections",
        sa.Column("declined_by_user_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "fan_connections",
        sa.Column(
            "requester_cooldown_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_fan_connections_declined_by_user_id",
        "fan_connections",
        "users",
        ["declined_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_fan_connections_requester_cooldown_until",
        "fan_connections",
        ["requester_cooldown_until"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_fan_connections_requester_cooldown_until", table_name="fan_connections")
    op.drop_constraint(
        "fk_fan_connections_declined_by_user_id",
        "fan_connections",
        type_="foreignkey",
    )
    op.drop_column("fan_connections", "requester_cooldown_until")
    op.drop_column("fan_connections", "declined_by_user_id")
