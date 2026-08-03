"""Allow dual host+platform referral attributions per order item.

Revision ID: 20260803_0218
Revises: 20260803_0217
Create Date: 2026-08-03
"""

from __future__ import annotations

from alembic import op

revision = "20260803_0218"
down_revision = "20260803_0217"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_referral_attributions_order_item",
        "referral_attributions",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_referral_attributions_order_item_payer",
        "referral_attributions",
        ["order_id", "attribution_item_key", "payer_type"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_referral_attributions_order_item_payer",
        "referral_attributions",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_referral_attributions_order_item",
        "referral_attributions",
        ["order_id", "attribution_item_key"],
    )
