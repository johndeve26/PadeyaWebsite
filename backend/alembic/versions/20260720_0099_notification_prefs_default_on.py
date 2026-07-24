"""Enable all email/push notification prefs by default.

Revision ID: 20260720_0099
Revises: 20260720_0098
Create Date: 2026-07-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260720_0099"
down_revision = "20260720_0098"
branch_labels = None
depends_on = None

_TOGGLE_COLUMNS = (
    "email_messages",
    "email_fan_connect",
    "email_marketing",
    "push_enabled",
    "push_messages",
    "push_message_previews",
    "push_fan_connect",
    "push_marketing",
)


def upgrade() -> None:
    # Existing rows: turn formerly-off defaults on. Keep marketing off when
    # the user already unsubscribed via one-click / preference unsubscribe.
    op.execute(
        sa.text(
            """
            UPDATE user_email_preferences
            SET
              email_messages = true,
              email_fan_connect = true,
              email_marketing = CASE
                WHEN unsubscribed_marketing_at IS NULL THEN true
                ELSE email_marketing
              END,
              push_enabled = true,
              push_messages = true,
              push_message_previews = true,
              push_fan_connect = true,
              push_marketing = CASE
                WHEN unsubscribed_marketing_at IS NULL THEN true
                ELSE push_marketing
              END,
              updated_at = NOW()
            """
        )
    )
    for col in _TOGGLE_COLUMNS:
        op.execute(
            sa.text(
                f"ALTER TABLE user_email_preferences "
                f"ALTER COLUMN {col} SET DEFAULT true"
            )
        )


def downgrade() -> None:
    # Restore prior server defaults only — do not flip user rows back off.
    prior_false = (
        "email_messages",
        "email_fan_connect",
        "email_marketing",
        "push_enabled",
        "push_messages",
        "push_message_previews",
        "push_fan_connect",
        "push_marketing",
    )
    for col in prior_false:
        op.execute(
            sa.text(
                f"ALTER TABLE user_email_preferences "
                f"ALTER COLUMN {col} SET DEFAULT false"
            )
        )
