"""Add fan_connect_settings.request_policies for multi-select request eligibility.

Revision ID: 20260720_0091
Revises: 20260720_0090
Create Date: 2026-07-20
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260720_0091"
down_revision = "20260720_0090"
branch_labels = None
depends_on = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.add_column(
        "fan_connect_settings",
        sa.Column(
            "request_policies",
            json_type,
            nullable=False,
            server_default=sa.text("'[\"same_event\"]'"),
        ),
    )
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, request_policy FROM fan_connect_settings")
    ).mappings()
    for row in rows:
        policy = row["request_policy"] or "same_event"
        payload = json.dumps([policy])
        if conn.dialect.name == "postgresql":
            conn.execute(
                sa.text(
                    "UPDATE fan_connect_settings "
                    "SET request_policies = CAST(:policies AS jsonb) "
                    "WHERE id = :id"
                ),
                {"policies": payload, "id": row["id"]},
            )
        else:
            conn.execute(
                sa.text(
                    "UPDATE fan_connect_settings "
                    "SET request_policies = :policies "
                    "WHERE id = :id"
                ),
                {"policies": payload, "id": row["id"]},
            )


def downgrade() -> None:
    op.drop_column("fan_connect_settings", "request_policies")
