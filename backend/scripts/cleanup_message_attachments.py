"""Expire unbound staged message attachments (never sent).

Safe to run on a cron. Soft-deletes rows and removes stored files.

Examples:
  python -m scripts.cleanup_message_attachments
  python -m scripts.cleanup_message_attachments --limit 500
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.messaging.service import cleanup_orphan_attachments

# Ensure ORM models are registered.
from app.auth import models as auth_models  # noqa: F401
from app.users import models as user_models  # noqa: F401
from app.hosts import models as host_models  # noqa: F401
from app.messaging import models as messaging_models  # noqa: F401


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clean up orphan Pàdéyá chat attachment uploads."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Max rows to process per run (default 500).",
    )
    args = parser.parse_args()
    db = SessionLocal()
    try:
        n = cleanup_orphan_attachments(db, limit=max(1, args.limit))
        print(f"expired_orphan_attachments={n}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
