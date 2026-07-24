"""Expand Vault access types and rule fields.

Revision ID: 20260717_0034
Revises: 20260717_0033
Create Date: 2026-07-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260717_0034"
down_revision = "20260717_0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vault_access_rules",
        sa.Column("price", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "vault_access_rules",
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="NGN"),
    )
    op.add_column(
        "vault_access_rules",
        sa.Column("required_ticket_type_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "vault_access_rules",
        sa.Column("required_legacy_tier", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "vault_access_rules",
        sa.Column("access_code", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "vault_access_rules",
        sa.Column("max_unlocks", sa.Integer(), nullable=True),
    )
    op.add_column(
        "vault_access_rules",
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "vault_access_rules",
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_vault_access_rules_required_ticket_type_id",
        "vault_access_rules",
        "ticket_types",
        ["required_ticket_type_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_vault_access_rules_required_ticket_type_id",
        "vault_access_rules",
        ["required_ticket_type_id"],
    )
    op.create_index(
        "ix_vault_access_rules_starts_at", "vault_access_rules", ["starts_at"]
    )
    op.create_index("ix_vault_access_rules_ends_at", "vault_access_rules", ["ends_at"])

    # Backfill rule price/currency from parent vault_items
    op.execute(
        """
        UPDATE vault_access_rules AS r
        SET price = i.price, currency = i.currency
        FROM vault_items AS i
        WHERE i.id = r.vault_item_id
        """
    )


def downgrade() -> None:
    op.drop_index("ix_vault_access_rules_ends_at", table_name="vault_access_rules")
    op.drop_index("ix_vault_access_rules_starts_at", table_name="vault_access_rules")
    op.drop_index(
        "ix_vault_access_rules_required_ticket_type_id", table_name="vault_access_rules"
    )
    op.drop_constraint(
        "fk_vault_access_rules_required_ticket_type_id",
        "vault_access_rules",
        type_="foreignkey",
    )
    op.drop_column("vault_access_rules", "ends_at")
    op.drop_column("vault_access_rules", "starts_at")
    op.drop_column("vault_access_rules", "max_unlocks")
    op.drop_column("vault_access_rules", "access_code")
    op.drop_column("vault_access_rules", "required_legacy_tier")
    op.drop_column("vault_access_rules", "required_ticket_type_id")
    op.drop_column("vault_access_rules", "currency")
    op.drop_column("vault_access_rules", "price")
