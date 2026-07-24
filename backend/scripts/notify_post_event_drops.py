"""Notify buyers when scheduled post-event merch drops go live.

  cd backend && source .venv/bin/activate && PYTHONPATH=. python scripts/notify_post_event_drops.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.merch.post_event_drops import notify_due_post_event_drops


def main() -> int:
    db = SessionLocal()
    try:
        sent = notify_due_post_event_drops(db, limit=20)
        print(f"post_event_drop_notifications_sent={sent}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
