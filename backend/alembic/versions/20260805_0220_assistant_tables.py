"""Create assistant conversation + knowledge tables.

Revision ID: 20260805_0220
Revises: 20260803_0219
Create Date: 2026-08-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260805_0220"
down_revision = "20260803_0219"
branch_labels = None
depends_on = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "assistant_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("anonymous_session_id", sa.String(length=64), nullable=True),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("active_role", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", JSON_TYPE, nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_assistant_sessions_user_id"),
        "assistant_sessions",
        ["user_id"],
    )
    op.create_index(
        op.f("ix_assistant_sessions_anonymous_session_id"),
        "assistant_sessions",
        ["anonymous_session_id"],
    )
    op.create_index(
        op.f("ix_assistant_sessions_expires_at"),
        "assistant_sessions",
        ["expires_at"],
    )

    op.create_table(
        "assistant_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("structured_content_json", JSON_TYPE, nullable=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("safety_status", sa.String(length=32), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["assistant_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_assistant_messages_session_id"),
        "assistant_messages",
        ["session_id"],
    )
    op.create_index(
        op.f("ix_assistant_messages_trace_id"),
        "assistant_messages",
        ["trace_id"],
    )

    op.create_table(
        "assistant_tool_calls",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=True),
        sa.Column("tool_name", sa.String(length=80), nullable=False),
        sa.Column("sanitized_arguments_json", JSON_TYPE, nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("confirmation_required", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["session_id"], ["assistant_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["message_id"], ["assistant_messages.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_assistant_tool_calls_session_id"),
        "assistant_tool_calls",
        ["session_id"],
    )
    op.create_index(
        op.f("ix_assistant_tool_calls_message_id"),
        "assistant_tool_calls",
        ["message_id"],
    )
    op.create_index(
        op.f("ix_assistant_tool_calls_tool_name"),
        "assistant_tool_calls",
        ["tool_name"],
    )

    op.create_table(
        "assistant_feedbacks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("rating", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=120), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["assistant_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["message_id"], ["assistant_messages.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_assistant_feedbacks_session_id"),
        "assistant_feedbacks",
        ["session_id"],
    )
    op.create_index(
        op.f("ix_assistant_feedbacks_message_id"),
        "assistant_feedbacks",
        ["message_id"],
    )
    op.create_index(
        op.f("ix_assistant_feedbacks_user_id"),
        "assistant_feedbacks",
        ["user_id"],
    )

    op.create_table(
        "assistant_action_confirmations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("tool_name", sa.String(length=80), nullable=False),
        sa.Column("sanitized_arguments_json", JSON_TYPE, nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result_json", JSON_TYPE, nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_assistant_action_confirmations_idempotency",
        ),
    )
    op.create_index(
        op.f("ix_assistant_action_confirmations_user_id"),
        "assistant_action_confirmations",
        ["user_id"],
    )
    op.create_index(
        op.f("ix_assistant_action_confirmations_status"),
        "assistant_action_confirmations",
        ["status"],
    )
    op.create_index(
        op.f("ix_assistant_action_confirmations_expires_at"),
        "assistant_action_confirmations",
        ["expires_at"],
    )

    op.create_table(
        "assistant_knowledge_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("canonical_url", sa.String(length=1000), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content_type", sa.String(length=64), nullable=True),
        sa.Column("route_group", sa.String(length=64), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("fetch_status", sa.String(length=32), nullable=True),
        sa.Column("metadata_json", JSON_TYPE, nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
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
        sa.UniqueConstraint(
            "canonical_url",
            name="uq_assistant_knowledge_documents_canonical_url",
        ),
    )
    op.create_index(
        op.f("ix_assistant_knowledge_documents_source_type"),
        "assistant_knowledge_documents",
        ["source_type"],
    )
    op.create_index(
        op.f("ix_assistant_knowledge_documents_route_group"),
        "assistant_knowledge_documents",
        ["route_group"],
    )
    op.create_index(
        op.f("ix_assistant_knowledge_documents_content_hash"),
        "assistant_knowledge_documents",
        ["content_hash"],
    )
    op.create_index(
        op.f("ix_assistant_knowledge_documents_status"),
        "assistant_knowledge_documents",
        ["status"],
    )

    op.create_table(
        "assistant_knowledge_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("heading_path", sa.String(length=500), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
        sa.Column("metadata_json", JSON_TYPE, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["assistant_knowledge_documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_assistant_knowledge_chunks_document_id"),
        "assistant_knowledge_chunks",
        ["document_id"],
    )
    op.create_index(
        "ix_assistant_knowledge_chunks_search_vector",
        "assistant_knowledge_chunks",
        ["search_vector"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_assistant_knowledge_chunks_search_vector",
        table_name="assistant_knowledge_chunks",
    )
    op.drop_index(
        op.f("ix_assistant_knowledge_chunks_document_id"),
        table_name="assistant_knowledge_chunks",
    )
    op.drop_table("assistant_knowledge_chunks")

    op.drop_index(
        op.f("ix_assistant_knowledge_documents_status"),
        table_name="assistant_knowledge_documents",
    )
    op.drop_index(
        op.f("ix_assistant_knowledge_documents_content_hash"),
        table_name="assistant_knowledge_documents",
    )
    op.drop_index(
        op.f("ix_assistant_knowledge_documents_route_group"),
        table_name="assistant_knowledge_documents",
    )
    op.drop_index(
        op.f("ix_assistant_knowledge_documents_source_type"),
        table_name="assistant_knowledge_documents",
    )
    op.drop_table("assistant_knowledge_documents")

    op.drop_index(
        op.f("ix_assistant_action_confirmations_expires_at"),
        table_name="assistant_action_confirmations",
    )
    op.drop_index(
        op.f("ix_assistant_action_confirmations_status"),
        table_name="assistant_action_confirmations",
    )
    op.drop_index(
        op.f("ix_assistant_action_confirmations_user_id"),
        table_name="assistant_action_confirmations",
    )
    op.drop_table("assistant_action_confirmations")

    op.drop_index(
        op.f("ix_assistant_feedbacks_user_id"), table_name="assistant_feedbacks"
    )
    op.drop_index(
        op.f("ix_assistant_feedbacks_message_id"),
        table_name="assistant_feedbacks",
    )
    op.drop_index(
        op.f("ix_assistant_feedbacks_session_id"),
        table_name="assistant_feedbacks",
    )
    op.drop_table("assistant_feedbacks")

    op.drop_index(
        op.f("ix_assistant_tool_calls_tool_name"),
        table_name="assistant_tool_calls",
    )
    op.drop_index(
        op.f("ix_assistant_tool_calls_message_id"),
        table_name="assistant_tool_calls",
    )
    op.drop_index(
        op.f("ix_assistant_tool_calls_session_id"),
        table_name="assistant_tool_calls",
    )
    op.drop_table("assistant_tool_calls")

    op.drop_index(
        op.f("ix_assistant_messages_trace_id"), table_name="assistant_messages"
    )
    op.drop_index(
        op.f("ix_assistant_messages_session_id"),
        table_name="assistant_messages",
    )
    op.drop_table("assistant_messages")

    op.drop_index(
        op.f("ix_assistant_sessions_expires_at"),
        table_name="assistant_sessions",
    )
    op.drop_index(
        op.f("ix_assistant_sessions_anonymous_session_id"),
        table_name="assistant_sessions",
    )
    op.drop_index(
        op.f("ix_assistant_sessions_user_id"), table_name="assistant_sessions"
    )
    op.drop_table("assistant_sessions")
