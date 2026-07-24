"""Ambassador eligibility: terms + program block.

Revision ID: 20260719_0077
Revises: 20260719_0076
Create Date: 2026-07-19

- users.ambassadors_blocked — platform block from ambassador programs
- ambassadors.terms_accepted_at / terms_version — recorded on open join
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260719_0077"
down_revision = "20260719_0076"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "ambassadors_blocked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "ambassadors",
        sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "ambassadors",
        sa.Column("terms_version", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ambassadors", "terms_version")
    op.drop_column("ambassadors", "terms_accepted_at")
    op.drop_column("users", "ambassadors_blocked")
