"""Default Fan Connect request policies to all open paths.

Revision ID: 20260729_0149
Revises: 20260729_0148
Create Date: 2026-07-29

New and existing users get same_event + same_host + public_passports ticked.
Nobody stays opt-in only; fans can still change settings afterward.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260729_0149"
down_revision = "20260729_0148"
branch_labels = None
depends_on = None

_DEFAULT_POLICIES_JSON = '["same_event", "same_host", "public_passports"]'


def upgrade() -> None:
    op.execute(
        sa.text(
            f"""
            UPDATE fan_connect_settings
            SET
              request_policies = '{_DEFAULT_POLICIES_JSON}'::jsonb,
              request_policy = 'public_passports',
              updated_at = NOW()
            """
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE fan_connect_settings "
            "ALTER COLUMN request_policy SET DEFAULT 'public_passports'"
        )
    )
    op.execute(
        sa.text(
            f"""
            ALTER TABLE fan_connect_settings
            ALTER COLUMN request_policies SET DEFAULT '{_DEFAULT_POLICIES_JSON}'::jsonb
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE fan_connect_settings "
            "ALTER COLUMN request_policy SET DEFAULT 'same_event'"
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE fan_connect_settings
            ALTER COLUMN request_policies SET DEFAULT '["same_event"]'::jsonb
            """
        )
    )
