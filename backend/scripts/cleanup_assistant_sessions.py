"""Cleanup expired assistant sessions, confirmations, and optional retention.

Examples:
  python -m scripts.cleanup_assistant_sessions
  python -m scripts.cleanup_assistant_sessions --dry-run

Bounded and idempotent. Safe to run on a cron.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, or_, select

from app.assistant.models import (
    AssistantActionConfirmation,
    AssistantSession,
)
from app.core.config import get_settings
from app.core.database import SessionLocal

from app.assistant import models as assistant_models  # noqa: F401


def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup assistant sessions/confirmations")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    now = datetime.now(UTC)
    public_hours = int(
        getattr(settings, "assistant_public_session_retention_hours", 24) or 24
    )
    auth_days = int(getattr(settings, "assistant_session_retention_days", 30) or 30)
    public_cutoff = now - timedelta(hours=public_hours)
    auth_cutoff = now - timedelta(days=auth_days)

    db = SessionLocal()
    try:
        expired_confirmations = db.scalars(
            select(AssistantActionConfirmation).where(
                or_(
                    AssistantActionConfirmation.expires_at < now,
                    AssistantActionConfirmation.status == "pending",
                ),
                AssistantActionConfirmation.expires_at < now,
            )
        ).all()

        public_sessions = db.scalars(
            select(AssistantSession).where(
                AssistantSession.user_id.is_(None),
                or_(
                    AssistantSession.expires_at < now,
                    AssistantSession.updated_at < public_cutoff,
                ),
            )
        ).all()

        auth_sessions = db.scalars(
            select(AssistantSession).where(
                AssistantSession.user_id.is_not(None),
                or_(
                    AssistantSession.expires_at < now,
                    AssistantSession.updated_at < auth_cutoff,
                ),
            )
        ).all()

        print(
            f"Would expire confirmations={len(expired_confirmations)} "
            f"public_sessions={len(public_sessions)} auth_sessions={len(auth_sessions)}"
        )
        if args.dry_run:
            return 0

        for row in expired_confirmations:
            if row.status == "pending":
                row.status = "expired"
        for session in [*public_sessions, *auth_sessions]:
            db.delete(session)
        db.commit()
        print("Cleanup committed.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
