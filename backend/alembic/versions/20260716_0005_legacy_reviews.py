"""legacy page verified reviews

Revision ID: 20260716_0005
Revises: 20260716_0004
Create Date: 2026-07-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260716_0005"
down_revision: Union[str, Sequence[str], None] = "20260716_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "host_legacy_scores",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("events_hosted", sa.Integer(), nullable=False),
        sa.Column("tickets_sold", sa.Integer(), nullable=False),
        sa.Column("verified_checkins", sa.Integer(), nullable=False),
        sa.Column("average_verified_rating", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("review_count", sa.Integer(), nullable=False),
        sa.Column("followers", sa.Integer(), nullable=False),
        sa.Column("repeat_buyers_rate", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("refund_dispute_rate", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("legacy_status", sa.String(length=64), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("host_id", name="uq_host_legacy_scores_host_id"),
    )
    op.create_index("ix_host_legacy_scores_host_id", "host_legacy_scores", ["host_id"], unique=False)

    op.create_table(
        "verified_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_user_id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("moderation_reason", sa.Text(), nullable=True),
        sa.Column("moderated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_id", name="uq_verified_reviews_ticket_id"),
        sa.UniqueConstraint(
            "event_id", "reviewer_user_id", name="uq_verified_reviews_event_reviewer"
        ),
    )
    op.create_index("ix_verified_reviews_event_id", "verified_reviews", ["event_id"], unique=False)
    op.create_index("ix_verified_reviews_host_id", "verified_reviews", ["host_id"], unique=False)
    op.create_index(
        "ix_verified_reviews_reviewer_user_id",
        "verified_reviews",
        ["reviewer_user_id"],
        unique=False,
    )
    op.create_index("ix_verified_reviews_ticket_id", "verified_reviews", ["ticket_id"], unique=False)
    op.create_index("ix_verified_reviews_status", "verified_reviews", ["status"], unique=False)
    op.create_index("ix_verified_reviews_created_at", "verified_reviews", ["created_at"], unique=False)

    op.create_table(
        "review_replies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("review_id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("author_user_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
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
        sa.ForeignKeyConstraint(["review_id"], ["verified_reviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("review_id", name="uq_review_replies_review_id"),
    )
    op.create_index("ix_review_replies_review_id", "review_replies", ["review_id"], unique=False)
    op.create_index("ix_review_replies_host_id", "review_replies", ["host_id"], unique=False)
    op.create_index(
        "ix_review_replies_author_user_id", "review_replies", ["author_user_id"], unique=False
    )

    op.create_table(
        "review_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("review_id", sa.Uuid(), nullable=False),
        sa.Column("reporter_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["review_id"], ["verified_reviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "review_id", "reporter_user_id", name="uq_review_reports_review_reporter"
        ),
    )
    op.create_index("ix_review_reports_review_id", "review_reports", ["review_id"], unique=False)
    op.create_index(
        "ix_review_reports_reporter_user_id", "review_reports", ["reporter_user_id"], unique=False
    )
    op.create_index("ix_review_reports_status", "review_reports", ["status"], unique=False)
    op.create_index("ix_review_reports_created_at", "review_reports", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_review_reports_created_at", table_name="review_reports")
    op.drop_index("ix_review_reports_status", table_name="review_reports")
    op.drop_index("ix_review_reports_reporter_user_id", table_name="review_reports")
    op.drop_index("ix_review_reports_review_id", table_name="review_reports")
    op.drop_table("review_reports")

    op.drop_index("ix_review_replies_author_user_id", table_name="review_replies")
    op.drop_index("ix_review_replies_host_id", table_name="review_replies")
    op.drop_index("ix_review_replies_review_id", table_name="review_replies")
    op.drop_table("review_replies")

    op.drop_index("ix_verified_reviews_created_at", table_name="verified_reviews")
    op.drop_index("ix_verified_reviews_status", table_name="verified_reviews")
    op.drop_index("ix_verified_reviews_ticket_id", table_name="verified_reviews")
    op.drop_index("ix_verified_reviews_reviewer_user_id", table_name="verified_reviews")
    op.drop_index("ix_verified_reviews_host_id", table_name="verified_reviews")
    op.drop_index("ix_verified_reviews_event_id", table_name="verified_reviews")
    op.drop_table("verified_reviews")

    op.drop_index("ix_host_legacy_scores_host_id", table_name="host_legacy_scores")
    op.drop_table("host_legacy_scores")
