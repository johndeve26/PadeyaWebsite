"""vault items media access purchases views

Revision ID: 20260716_0010
Revises: 20260716_0009
Create Date: 2026-07-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260716_0010"
down_revision: Union[str, Sequence[str], None] = "20260716_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vault_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("preview_text", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("cover_url", sa.String(length=500), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("moderation_status", sa.String(length=32), nullable=False),
        sa.Column("moderation_note", sa.Text(), nullable=True),
        sa.Column("moderated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["moderated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("host_id", "slug", name="uq_vault_items_host_slug"),
    )
    op.create_index("ix_vault_items_host_id", "vault_items", ["host_id"])
    op.create_index("ix_vault_items_slug", "vault_items", ["slug"])
    op.create_index("ix_vault_items_content_type", "vault_items", ["content_type"])
    op.create_index("ix_vault_items_status", "vault_items", ["status"])
    op.create_index("ix_vault_items_moderation_status", "vault_items", ["moderation_status"])
    op.create_index("ix_vault_items_created_at", "vault_items", ["created_at"])

    op.create_table(
        "vault_media",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vault_item_id", sa.Uuid(), nullable=False),
        sa.Column("media_type", sa.String(length=64), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=True),
        sa.Column("label", sa.String(length=160), nullable=True),
        sa.Column("is_preview", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["vault_item_id"], ["vault_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vault_media_vault_item_id", "vault_media", ["vault_item_id"])

    op.create_table(
        "vault_access_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vault_item_id", sa.Uuid(), nullable=False),
        sa.Column("access_type", sa.String(length=64), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("ticket_type_ids", sa.JSON(), nullable=True),
        sa.Column("require_check_in", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["vault_item_id"], ["vault_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vault_item_id", name="uq_vault_access_rules_item"),
    )
    op.create_index("ix_vault_access_rules_vault_item_id", "vault_access_rules", ["vault_item_id"])
    op.create_index("ix_vault_access_rules_access_type", "vault_access_rules", ["access_type"])
    op.create_index("ix_vault_access_rules_event_id", "vault_access_rules", ["event_id"])

    op.create_table(
        "vault_purchases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vault_item_id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payment_reference", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("authorization_url", sa.String(length=500), nullable=True),
        sa.Column("access_code", sa.String(length=128), nullable=True),
        sa.Column("provider_payment_id", sa.String(length=128), nullable=True),
        sa.Column("raw_response", sa.JSON(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vault_item_id"], ["vault_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_reference"),
        sa.UniqueConstraint(
            "vault_item_id",
            "user_id",
            "payment_reference",
            name="uq_vault_purchases_item_user_ref",
        ),
    )
    op.create_index("ix_vault_purchases_vault_item_id", "vault_purchases", ["vault_item_id"])
    op.create_index("ix_vault_purchases_host_id", "vault_purchases", ["host_id"])
    op.create_index("ix_vault_purchases_user_id", "vault_purchases", ["user_id"])
    op.create_index("ix_vault_purchases_status", "vault_purchases", ["status"])
    op.create_index("ix_vault_purchases_payment_reference", "vault_purchases", ["payment_reference"])
    op.create_index("ix_vault_purchases_created_at", "vault_purchases", ["created_at"])

    op.create_table(
        "vault_views",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vault_item_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("had_access", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["vault_item_id"], ["vault_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vault_views_vault_item_id", "vault_views", ["vault_item_id"])
    op.create_index("ix_vault_views_user_id", "vault_views", ["user_id"])
    op.create_index("ix_vault_views_created_at", "vault_views", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_vault_views_created_at", table_name="vault_views")
    op.drop_index("ix_vault_views_user_id", table_name="vault_views")
    op.drop_index("ix_vault_views_vault_item_id", table_name="vault_views")
    op.drop_table("vault_views")
    op.drop_index("ix_vault_purchases_created_at", table_name="vault_purchases")
    op.drop_index("ix_vault_purchases_payment_reference", table_name="vault_purchases")
    op.drop_index("ix_vault_purchases_status", table_name="vault_purchases")
    op.drop_index("ix_vault_purchases_user_id", table_name="vault_purchases")
    op.drop_index("ix_vault_purchases_host_id", table_name="vault_purchases")
    op.drop_index("ix_vault_purchases_vault_item_id", table_name="vault_purchases")
    op.drop_table("vault_purchases")
    op.drop_index("ix_vault_access_rules_event_id", table_name="vault_access_rules")
    op.drop_index("ix_vault_access_rules_access_type", table_name="vault_access_rules")
    op.drop_index("ix_vault_access_rules_vault_item_id", table_name="vault_access_rules")
    op.drop_table("vault_access_rules")
    op.drop_index("ix_vault_media_vault_item_id", table_name="vault_media")
    op.drop_table("vault_media")
    op.drop_index("ix_vault_items_created_at", table_name="vault_items")
    op.drop_index("ix_vault_items_moderation_status", table_name="vault_items")
    op.drop_index("ix_vault_items_status", table_name="vault_items")
    op.drop_index("ix_vault_items_content_type", table_name="vault_items")
    op.drop_index("ix_vault_items_slug", table_name="vault_items")
    op.drop_index("ix_vault_items_host_id", table_name="vault_items")
    op.drop_table("vault_items")
