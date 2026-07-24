"""Vault item types + metadata fields.

Revision ID: 20260717_0033
Revises: 20260717_0032
Create Date: 2026-07-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260717_0033"
down_revision = "20260717_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

    op.add_column("vault_items", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("vault_items", sa.Column("file_url", sa.String(length=500), nullable=True))
    op.add_column(
        "vault_items", sa.Column("external_url", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "vault_items",
        sa.Column("related_event_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "vault_items",
        sa.Column("related_memory_id", sa.Uuid(), nullable=True),
    )
    op.add_column("vault_items", sa.Column("tags", json_type, nullable=True))
    op.add_column(
        "vault_items",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_foreign_key(
        "fk_vault_items_related_event_id",
        "vault_items",
        "events",
        ["related_event_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_vault_items_related_memory_id",
        "vault_items",
        "event_memories",
        ["related_memory_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_vault_items_related_event_id", "vault_items", ["related_event_id"]
    )
    op.create_index(
        "ix_vault_items_related_memory_id", "vault_items", ["related_memory_id"]
    )
    op.create_index("ix_vault_items_expires_at", "vault_items", ["expires_at"])

    # Migrate legacy content_type values
    op.execute(
        "UPDATE vault_items SET content_type = 'file_download' WHERE content_type = 'file'"
    )
    op.execute(
        "UPDATE vault_items SET content_type = 'ticket_holder_recap' "
        "WHERE content_type = 'livestream_replay'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE vault_items SET content_type = 'file' WHERE content_type = 'file_download'"
    )
    op.execute(
        "UPDATE vault_items SET content_type = 'livestream_replay' "
        "WHERE content_type = 'ticket_holder_recap'"
    )

    op.drop_index("ix_vault_items_expires_at", table_name="vault_items")
    op.drop_index("ix_vault_items_related_memory_id", table_name="vault_items")
    op.drop_index("ix_vault_items_related_event_id", table_name="vault_items")
    op.drop_constraint("fk_vault_items_related_memory_id", "vault_items", type_="foreignkey")
    op.drop_constraint("fk_vault_items_related_event_id", "vault_items", type_="foreignkey")
    op.drop_column("vault_items", "expires_at")
    op.drop_column("vault_items", "tags")
    op.drop_column("vault_items", "related_memory_id")
    op.drop_column("vault_items", "related_event_id")
    op.drop_column("vault_items", "external_url")
    op.drop_column("vault_items", "file_url")
    op.drop_column("vault_items", "description")
