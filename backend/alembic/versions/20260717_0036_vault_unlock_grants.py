"""Vault access grants + unlock attempts for idempotent one-time unlocks.

Revision ID: 20260717_0036
Revises: 20260717_0035
Create Date: 2026-07-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260717_0036"
down_revision = "20260717_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vault_access_grants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vault_item_id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("vault_purchase_id", sa.Uuid(), nullable=True),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["host_id"], ["hosts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["vault_item_id"], ["vault_items.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["vault_purchase_id"],
            ["vault_purchases.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "vault_item_id",
            "user_id",
            name="uq_vault_access_grants_item_user",
        ),
    )
    op.create_index(
        "ix_vault_access_grants_vault_item_id",
        "vault_access_grants",
        ["vault_item_id"],
    )
    op.create_index(
        "ix_vault_access_grants_host_id", "vault_access_grants", ["host_id"]
    )
    op.create_index(
        "ix_vault_access_grants_user_id", "vault_access_grants", ["user_id"]
    )
    op.create_index(
        "ix_vault_access_grants_source", "vault_access_grants", ["source"]
    )
    op.create_index(
        "ix_vault_access_grants_vault_purchase_id",
        "vault_access_grants",
        ["vault_purchase_id"],
    )
    op.create_index(
        "ix_vault_access_grants_created_at",
        "vault_access_grants",
        ["created_at"],
    )

    op.create_table(
        "vault_unlock_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vault_item_id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("vault_purchase_id", sa.Uuid(), nullable=True),
        sa.Column("payment_reference", sa.String(length=64), nullable=True),
        sa.Column("detail", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["host_id"], ["hosts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["vault_item_id"], ["vault_items.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["vault_purchase_id"],
            ["vault_purchases.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_vault_unlock_attempts_vault_item_id",
        "vault_unlock_attempts",
        ["vault_item_id"],
    )
    op.create_index(
        "ix_vault_unlock_attempts_host_id",
        "vault_unlock_attempts",
        ["host_id"],
    )
    op.create_index(
        "ix_vault_unlock_attempts_user_id",
        "vault_unlock_attempts",
        ["user_id"],
    )
    op.create_index(
        "ix_vault_unlock_attempts_status",
        "vault_unlock_attempts",
        ["status"],
    )
    op.create_index(
        "ix_vault_unlock_attempts_vault_purchase_id",
        "vault_unlock_attempts",
        ["vault_purchase_id"],
    )
    op.create_index(
        "ix_vault_unlock_attempts_created_at",
        "vault_unlock_attempts",
        ["created_at"],
    )

    # Backfill grants from existing paid purchases (one grant per user+item)
    op.execute(
        """
        INSERT INTO vault_access_grants (
            id, vault_item_id, host_id, user_id, source,
            vault_purchase_id, granted_at, created_at
        )
        SELECT DISTINCT ON (p.vault_item_id, p.user_id)
            gen_random_uuid(),
            p.vault_item_id,
            p.host_id,
            p.user_id,
            CASE
                WHEN p.provider IN ('invite_code', 'manual_grant', 'demo', 'internal')
                    THEN p.provider
                ELSE 'purchase'
            END,
            p.id,
            COALESCE(p.paid_at, p.created_at),
            COALESCE(p.paid_at, p.created_at)
        FROM vault_purchases p
        WHERE p.status = 'paid'
        ORDER BY p.vault_item_id, p.user_id, p.paid_at ASC NULLS LAST, p.created_at ASC
        ON CONFLICT (vault_item_id, user_id) DO NOTHING
        """
    )

    # Idempotent ledger uniqueness for vault sale credits
    op.create_index(
        "uq_ledger_vault_sale_purchase",
        "ledger_entries",
        ["reference_id"],
        unique=True,
        postgresql_where=sa.text(
            "entry_type = 'vault_sale' AND reference_type = 'vault_purchase'"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_ledger_vault_sale_purchase",
        table_name="ledger_entries",
    )
    op.drop_index("ix_vault_unlock_attempts_created_at", table_name="vault_unlock_attempts")
    op.drop_index(
        "ix_vault_unlock_attempts_vault_purchase_id",
        table_name="vault_unlock_attempts",
    )
    op.drop_index("ix_vault_unlock_attempts_status", table_name="vault_unlock_attempts")
    op.drop_index("ix_vault_unlock_attempts_user_id", table_name="vault_unlock_attempts")
    op.drop_index("ix_vault_unlock_attempts_host_id", table_name="vault_unlock_attempts")
    op.drop_index(
        "ix_vault_unlock_attempts_vault_item_id",
        table_name="vault_unlock_attempts",
    )
    op.drop_table("vault_unlock_attempts")

    op.drop_index("ix_vault_access_grants_created_at", table_name="vault_access_grants")
    op.drop_index(
        "ix_vault_access_grants_vault_purchase_id",
        table_name="vault_access_grants",
    )
    op.drop_index("ix_vault_access_grants_source", table_name="vault_access_grants")
    op.drop_index("ix_vault_access_grants_user_id", table_name="vault_access_grants")
    op.drop_index("ix_vault_access_grants_host_id", table_name="vault_access_grants")
    op.drop_index(
        "ix_vault_access_grants_vault_item_id",
        table_name="vault_access_grants",
    )
    op.drop_table("vault_access_grants")
