"""Open Event Ambassadors: event flags + ambassador scope.

Revision ID: 20260719_0076
Revises: 20260719_0075
Create Date: 2026-07-19

- events.open_ambassadors_enabled (bool, default false)
- events.open_ambassador_commission_percent (numeric 5,2, default 5.00)
- ambassadors.event_id (nullable FK)
- ambassadors.program_kind (host_curated | open_event)
- Replace host-wide unique referral with partial uniques for curated vs open
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260719_0076"
down_revision = "20260719_0075"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column(
            "open_ambassadors_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "events",
        sa.Column(
            "open_ambassador_commission_percent",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            server_default="5.00",
        ),
    )

    op.add_column("ambassadors", sa.Column("event_id", sa.Uuid(), nullable=True))
    op.add_column(
        "ambassadors",
        sa.Column(
            "program_kind",
            sa.String(length=32),
            nullable=False,
            server_default="host_curated",
        ),
    )
    op.create_foreign_key(
        "fk_ambassadors_event_id",
        "ambassadors",
        "events",
        ["event_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_ambassadors_event_id", "ambassadors", ["event_id"], unique=False)
    op.create_index(
        "ix_ambassadors_program_kind", "ambassadors", ["program_kind"], unique=False
    )

    op.drop_constraint("uq_ambassadors_host_referral", "ambassadors", type_="unique")
    op.create_index(
        "uq_ambassadors_host_referral_curated",
        "ambassadors",
        ["host_id", "referral_code"],
        unique=True,
        postgresql_where=sa.text("event_id IS NULL"),
        sqlite_where=sa.text("event_id IS NULL"),
    )
    op.create_index(
        "uq_ambassadors_event_referral",
        "ambassadors",
        ["event_id", "referral_code"],
        unique=True,
        postgresql_where=sa.text("event_id IS NOT NULL"),
        sqlite_where=sa.text("event_id IS NOT NULL"),
    )
    op.create_index(
        "uq_ambassadors_event_user",
        "ambassadors",
        ["event_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("event_id IS NOT NULL AND user_id IS NOT NULL"),
        sqlite_where=sa.text("event_id IS NOT NULL AND user_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_ambassadors_event_user", table_name="ambassadors")
    op.drop_index("uq_ambassadors_event_referral", table_name="ambassadors")
    op.drop_index("uq_ambassadors_host_referral_curated", table_name="ambassadors")
    op.create_unique_constraint(
        "uq_ambassadors_host_referral",
        "ambassadors",
        ["host_id", "referral_code"],
    )
    op.drop_index("ix_ambassadors_program_kind", table_name="ambassadors")
    op.drop_index("ix_ambassadors_event_id", table_name="ambassadors")
    op.drop_constraint("fk_ambassadors_event_id", "ambassadors", type_="foreignkey")
    op.drop_column("ambassadors", "program_kind")
    op.drop_column("ambassadors", "event_id")
    op.drop_column("events", "open_ambassador_commission_percent")
    op.drop_column("events", "open_ambassadors_enabled")
