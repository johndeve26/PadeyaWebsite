"""demo entity markers and support cases

Revision ID: 20260716_0017
Revises: 20260716_0016
Create Date: 2026-07-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260716_0017"
down_revision: Union[str, Sequence[str], None] = "20260716_0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "demo_entity_markers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_key", sa.String(length=255), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column(
            "meta",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_type", "entity_key", name="uq_demo_entity_markers"),
    )
    op.create_index(
        op.f("ix_demo_entity_markers_entity_type"),
        "demo_entity_markers",
        ["entity_type"],
        unique=False,
    )

    op.create_table(
        "demo_support_cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_key", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("requester_email", sa.String(length=320), nullable=False),
        sa.Column("assignee_email", sa.String(length=320), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("escalation", sa.String(length=120), nullable=True),
        sa.Column(
            "meta",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_key"),
    )
    op.create_index(
        op.f("ix_demo_support_cases_case_key"),
        "demo_support_cases",
        ["case_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_demo_support_cases_status"),
        "demo_support_cases",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_demo_support_cases_status"), table_name="demo_support_cases")
    op.drop_index(op.f("ix_demo_support_cases_case_key"), table_name="demo_support_cases")
    op.drop_table("demo_support_cases")
    op.drop_index(
        op.f("ix_demo_entity_markers_entity_type"), table_name="demo_entity_markers"
    )
    op.drop_table("demo_entity_markers")
