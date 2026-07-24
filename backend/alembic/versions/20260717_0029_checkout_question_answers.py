"""Checkout question help_text + order answer storage.

Revision ID: 20260717_0029
Revises: 20260717_0028
Create Date: 2026-07-17
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260717_0029"
down_revision: Union[str, Sequence[str], None] = "20260717_0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "event_checkout_questions",
        sa.Column("help_text", sa.Text(), nullable=True),
    )
    op.create_table(
        "order_checkout_answers",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("order_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("question_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("question_label", sa.String(length=255), nullable=False),
        sa.Column("question_type", sa.String(length=32), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["event_checkout_questions.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_order_checkout_answers_order_id",
        "order_checkout_answers",
        ["order_id"],
    )
    op.create_index(
        "ix_order_checkout_answers_question_id",
        "order_checkout_answers",
        ["question_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_order_checkout_answers_question_id",
        table_name="order_checkout_answers",
    )
    op.drop_index(
        "ix_order_checkout_answers_order_id",
        table_name="order_checkout_answers",
    )
    op.drop_table("order_checkout_answers")
    op.drop_column("event_checkout_questions", "help_text")
