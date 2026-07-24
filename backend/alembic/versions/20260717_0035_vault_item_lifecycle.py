"""Vault item lifecycle statuses + archive metadata.

Revision ID: 20260717_0035
Revises: 20260717_0034
Create Date: 2026-07-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260717_0035"
down_revision = "20260717_0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vault_items",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "vault_items",
        sa.Column("archived_by", sa.Uuid(), nullable=True),
    )
    op.create_index("ix_vault_items_archived_at", "vault_items", ["archived_at"])
    op.create_foreign_key(
        "fk_vault_items_archived_by",
        "vault_items",
        "users",
        ["archived_by"],
        ["id"],
        ondelete="SET NULL",
    )
    # Legacy archive marker → canonical archived status
    op.execute("UPDATE vault_items SET status = 'archived' WHERE status = 'disabled'")
    op.execute("UPDATE vault_items SET status = 'draft' WHERE status = 'flagged'")


def downgrade() -> None:
    op.execute("UPDATE vault_items SET status = 'disabled' WHERE status = 'archived'")
    op.execute(
        "UPDATE vault_items SET status = 'disabled' WHERE status = 'hidden_by_admin'"
    )
    op.execute("UPDATE vault_items SET status = 'published' WHERE status = 'scheduled'")
    op.execute("UPDATE vault_items SET status = 'published' WHERE status = 'expired'")
    op.drop_constraint("fk_vault_items_archived_by", "vault_items", type_="foreignkey")
    op.drop_index("ix_vault_items_archived_at", table_name="vault_items")
    op.drop_column("vault_items", "archived_by")
    op.drop_column("vault_items", "archived_at")
