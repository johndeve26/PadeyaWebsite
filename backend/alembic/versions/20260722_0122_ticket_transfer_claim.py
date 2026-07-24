"""Ticket transfer claim tokens for recipients without accounts."""

from alembic import op
import sqlalchemy as sa

revision = "20260722_0122"
down_revision = "20260721_0121"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "ticket_transfers",
        "to_user_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.add_column(
        "ticket_transfers",
        sa.Column("recipient_name", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "ticket_transfers",
        sa.Column("claim_token_hash", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "ticket_transfers",
        sa.Column("claim_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ticket_transfers", "claim_token_expires_at")
    op.drop_column("ticket_transfers", "claim_token_hash")
    op.drop_column("ticket_transfers", "recipient_name")
    op.alter_column(
        "ticket_transfers",
        "to_user_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
