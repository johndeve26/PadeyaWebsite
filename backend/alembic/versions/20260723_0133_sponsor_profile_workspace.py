"""Sponsor profile workspace — extend sponsors, team, admin notes

Revision ID: 20260723_0133
Revises: 20260722_0132
Create Date: 2026-07-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260723_0133"
down_revision: Union[str, Sequence[str], None] = "20260722_0132"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sponsors",
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "sponsors",
        sa.Column("display_name", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "sponsors",
        sa.Column("slug", sa.String(length=180), nullable=True),
    )
    op.add_column(
        "sponsors",
        sa.Column("sponsor_type", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "sponsors",
        sa.Column("cover_image_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "sponsors",
        sa.Column("short_bio", sa.Text(), nullable=True),
    )
    op.add_column(
        "sponsors",
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.add_column(
        "sponsors",
        sa.Column("website_url", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "sponsors",
        sa.Column("industry", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "sponsors",
        sa.Column("categories", sa.JSON(), nullable=True),
    )
    op.add_column(
        "sponsors",
        sa.Column("target_locations", sa.JSON(), nullable=True),
    )
    op.add_column(
        "sponsors",
        sa.Column("budget_range", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "sponsors",
        sa.Column("campaign_goals", sa.JSON(), nullable=True),
    )
    op.add_column(
        "sponsors",
        sa.Column("contact_phone", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "sponsors",
        sa.Column("verification_status", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "sponsors",
        sa.Column("visibility", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "sponsors",
        sa.Column("sponsor_ready_score", sa.Integer(), nullable=True),
    )
    op.add_column(
        "sponsors",
        sa.Column("onboarding_status", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "sponsors",
        sa.Column("internal_notes", sa.Text(), nullable=True),
    )

    op.execute(
        """
        UPDATE sponsors SET
            owner_user_id = user_id,
            display_name = company_name,
            website_url = website,
            verification_status = COALESCE(verification_status, 'unverified'),
            visibility = COALESCE(visibility, 'private'),
            onboarding_status = COALESCE(onboarding_status, 'legacy'),
            sponsor_type = COALESCE(sponsor_type, 'other'),
            short_bio = COALESCE(short_bio, ''),
            description = COALESCE(description, '')
        """
    )

    op.create_index("ix_sponsors_owner_user_id", "sponsors", ["owner_user_id"])
    op.create_index("ix_sponsors_slug", "sponsors", ["slug"], unique=True)
    op.create_index("ix_sponsors_sponsor_type", "sponsors", ["sponsor_type"])
    op.create_index("ix_sponsors_verification_status", "sponsors", ["verification_status"])
    op.create_index("ix_sponsors_visibility", "sponsors", ["visibility"])
    op.create_foreign_key(
        "fk_sponsors_owner_user_id_users",
        "sponsors",
        "users",
        ["owner_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "sponsor_team_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sponsor_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("permissions_json", sa.JSON(), nullable=True),
        sa.Column("invited_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
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
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["sponsor_id"], ["sponsors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["invited_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "sponsor_id", "user_id", name="uq_sponsor_team_members_sponsor_user"
        ),
    )
    op.create_index(
        "ix_sponsor_team_members_sponsor_id", "sponsor_team_members", ["sponsor_id"]
    )
    op.create_index(
        "ix_sponsor_team_members_user_id", "sponsor_team_members", ["user_id"]
    )


def downgrade() -> None:
    op.drop_table("sponsor_team_members")
    op.drop_constraint("fk_sponsors_owner_user_id_users", "sponsors", type_="foreignkey")
    op.drop_index("ix_sponsors_visibility", table_name="sponsors")
    op.drop_index("ix_sponsors_verification_status", table_name="sponsors")
    op.drop_index("ix_sponsors_sponsor_type", table_name="sponsors")
    op.drop_index("ix_sponsors_slug", table_name="sponsors")
    op.drop_index("ix_sponsors_owner_user_id", table_name="sponsors")
    for col in (
        "internal_notes",
        "onboarding_status",
        "sponsor_ready_score",
        "visibility",
        "verification_status",
        "contact_phone",
        "campaign_goals",
        "budget_range",
        "target_locations",
        "categories",
        "industry",
        "website_url",
        "description",
        "short_bio",
        "cover_image_url",
        "sponsor_type",
        "slug",
        "display_name",
        "owner_user_id",
    ):
        op.drop_column("sponsors", col)
