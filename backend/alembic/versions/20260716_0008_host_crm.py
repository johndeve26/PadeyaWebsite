"""host crm followers segments announcements

Revision ID: 20260716_0008
Revises: 20260716_0007
Create Date: 2026-07-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260716_0008"
down_revision: Union[str, Sequence[str], None] = "20260716_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "host_followers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("marketing_opt_in", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("host_id", "user_id", name="uq_host_followers_host_user"),
    )
    op.create_index("ix_host_followers_host_id", "host_followers", ["host_id"])
    op.create_index("ix_host_followers_user_id", "host_followers", ["user_id"])
    op.create_index("ix_host_followers_created_at", "host_followers", ["created_at"])

    op.create_table(
        "audience_segments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("segment_key", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("filters", sa.JSON(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("host_id", "slug", name="uq_audience_segments_host_slug"),
    )
    op.create_index("ix_audience_segments_host_id", "audience_segments", ["host_id"])
    op.create_index("ix_audience_segments_slug", "audience_segments", ["slug"])
    op.create_index("ix_audience_segments_segment_key", "audience_segments", ["segment_key"])

    op.create_table(
        "host_announcements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("segment_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body_email", sa.Text(), nullable=False),
        sa.Column("body_whatsapp", sa.Text(), nullable=True),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("delivery_status", sa.String(length=32), nullable=False),
        sa.Column("recipient_count", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["segment_id"], ["audience_segments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_host_announcements_host_id", "host_announcements", ["host_id"])
    op.create_index("ix_host_announcements_segment_id", "host_announcements", ["segment_id"])
    op.create_index("ix_host_announcements_status", "host_announcements", ["status"])
    op.create_index("ix_host_announcements_created_at", "host_announcements", ["created_at"])

    op.create_table(
        "announcement_recipients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("announcement_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("skip_reason", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["announcement_id"], ["host_announcements.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "announcement_id",
            "user_id",
            name="uq_announcement_recipients_announcement_user",
        ),
    )
    op.create_index(
        "ix_announcement_recipients_announcement_id",
        "announcement_recipients",
        ["announcement_id"],
    )
    op.create_index("ix_announcement_recipients_user_id", "announcement_recipients", ["user_id"])
    op.create_index("ix_announcement_recipients_status", "announcement_recipients", ["status"])


def downgrade() -> None:
    op.drop_table("announcement_recipients")
    op.drop_table("host_announcements")
    op.drop_table("audience_segments")
    op.drop_table("host_followers")
