"""Fan Connect + Passport discoverability on by default.

Revision ID: 20260724_0140
Revises: 20260723_0139
Create Date: 2026-07-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260724_0140"
down_revision = "20260723_0139"
branch_labels = None
depends_on = None

_CONNECT_TOGGLES = (
    "fan_connect_enabled",
    "discoverable_for_same_events",
    "discoverable_for_similar_interests",
    "allow_connection_requests",
    "show_public_city",
)


def upgrade() -> None:
    # Existing Fan Connect settings rows: turn formerly-off defaults on.
    op.execute(
        sa.text(
            """
            UPDATE fan_connect_settings
            SET
              fan_connect_enabled = true,
              discoverable_for_same_events = true,
              discoverable_for_similar_interests = true,
              allow_connection_requests = true,
              show_public_city = true,
              updated_at = NOW()
            """
        )
    )
    # Users without a settings row yet get one with everything on.
    op.execute(
        sa.text(
            """
            INSERT INTO fan_connect_settings (
              id,
              user_id,
              fan_connect_enabled,
              discoverable_for_same_events,
              discoverable_for_similar_interests,
              allow_connection_requests,
              show_shared_hosts,
              show_shared_categories,
              show_shared_public_events,
              show_public_city,
              hide_private_events_always,
              request_policy,
              request_policies,
              created_at,
              updated_at
            )
            SELECT
              gen_random_uuid(),
              u.id,
              true,
              true,
              true,
              true,
              true,
              true,
              true,
              true,
              true,
              'same_event',
              '["same_event"]'::jsonb,
              NOW(),
              NOW()
            FROM users u
            LEFT JOIN fan_connect_settings f ON f.user_id = u.id
            WHERE f.id IS NULL
            """
        )
    )
    for col in _CONNECT_TOGGLES:
        op.execute(
            sa.text(
                f"ALTER TABLE fan_connect_settings "
                f"ALTER COLUMN {col} SET DEFAULT true"
            )
        )

    # Passport: public + directory-visible by default (skip admin-hidden profiles).
    op.execute(
        sa.text(
            """
            UPDATE fan_passports
            SET
              visibility = 'public',
              appear_in_directory = true,
              updated_at = NOW()
            WHERE admin_hidden_at IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE fan_passports "
            "ALTER COLUMN visibility SET DEFAULT 'public'"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE fan_passports "
            "ALTER COLUMN appear_in_directory SET DEFAULT true"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE fan_passports "
            "ALTER COLUMN appear_in_directory SET DEFAULT false"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE fan_passports "
            "ALTER COLUMN visibility SET DEFAULT 'private'"
        )
    )
    for col in _CONNECT_TOGGLES:
        op.execute(
            sa.text(
                f"ALTER TABLE fan_connect_settings "
                f"ALTER COLUMN {col} SET DEFAULT false"
            )
        )
