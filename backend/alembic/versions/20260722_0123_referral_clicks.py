"""Canonical referral_clicks table for total vs unique ambassador metrics."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260722_0123"
down_revision = "20260722_0122"
branch_labels = None
depends_on = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "referral_clicks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ambassador_id", sa.Uuid(), nullable=True),
        sa.Column("participant_id", sa.Uuid(), nullable=True),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("merch_product_id", sa.Uuid(), nullable=True),
        sa.Column("host_id", sa.Uuid(), nullable=True),
        sa.Column("referral_code", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("visitor_hash", sa.String(length=64), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("user_agent_hash", sa.String(length=64), nullable=True),
        sa.Column("total_click_key", sa.String(length=64), nullable=True),
        sa.Column("unique_click_key", sa.String(length=64), nullable=True),
        sa.Column("is_unique_24h", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_duplicate_30s", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_qualified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("metadata_json", JSON_TYPE, nullable=True),
        sa.ForeignKeyConstraint(["ambassador_id"], ["ambassadors.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["participant_id"], ["ambassador_participants.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["ambassador_campaigns.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["merch_product_id"], ["event_merch_products.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_referral_clicks_referral_code", "referral_clicks", ["referral_code"]
    )
    op.create_index(
        "ix_referral_clicks_target_type", "referral_clicks", ["target_type"]
    )
    op.create_index("ix_referral_clicks_source", "referral_clicks", ["source"])
    op.create_index(
        "ix_referral_clicks_visitor_hash", "referral_clicks", ["visitor_hash"]
    )
    op.create_index("ix_referral_clicks_created_at", "referral_clicks", ["created_at"])
    op.create_index(
        "ix_referral_clicks_ambassador_created",
        "referral_clicks",
        ["ambassador_id", "created_at"],
    )
    op.create_index(
        "ix_referral_clicks_participant_created",
        "referral_clicks",
        ["participant_id", "created_at"],
    )
    op.create_index(
        "ix_referral_clicks_campaign_created",
        "referral_clicks",
        ["campaign_id", "created_at"],
    )
    op.create_index(
        "ix_referral_clicks_unique_key_created",
        "referral_clicks",
        ["unique_click_key", "created_at"],
    )
    op.create_index(
        "ix_referral_clicks_total_key_created",
        "referral_clicks",
        ["total_click_key", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_referral_clicks_total_key_created", table_name="referral_clicks")
    op.drop_index("ix_referral_clicks_unique_key_created", table_name="referral_clicks")
    op.drop_index("ix_referral_clicks_campaign_created", table_name="referral_clicks")
    op.drop_index("ix_referral_clicks_participant_created", table_name="referral_clicks")
    op.drop_index("ix_referral_clicks_ambassador_created", table_name="referral_clicks")
    op.drop_index("ix_referral_clicks_created_at", table_name="referral_clicks")
    op.drop_index("ix_referral_clicks_visitor_hash", table_name="referral_clicks")
    op.drop_index("ix_referral_clicks_source", table_name="referral_clicks")
    op.drop_index("ix_referral_clicks_target_type", table_name="referral_clicks")
    op.drop_index("ix_referral_clicks_referral_code", table_name="referral_clicks")
    op.drop_table("referral_clicks")
