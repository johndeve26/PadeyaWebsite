"""Rewrite legacy Smartlance demo static URLs to site-relative /demo/... paths.

Usage (from backend/):
  PYTHONPATH=. python scripts/backfill_legacy_demo_urls.py --dry-run
  PYTHONPATH=. python scripts/backfill_legacy_demo_urls.py --apply

Only changes:
  https://padeya.smartlancedesigns.com/demo/...
→ /demo/...

Never prints secrets. Idempotent / safe to rerun.
"""

from __future__ import annotations

import argparse
import json
import sys

from app.core.database import SessionLocal
from app.demo.legacy_url_backfill import backfill_legacy_smartlance_demo_urls


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill padeya.smartlancedesigns.com/demo/... → /demo/..."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without committing (default if --apply omitted)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit rewrites to the database",
    )
    args = parser.parse_args()
    dry_run = not args.apply
    if args.dry_run:
        dry_run = True

    db = SessionLocal()
    try:
        stats = backfill_legacy_smartlance_demo_urls(db, dry_run=dry_run)
    finally:
        db.close()

    print(
        json.dumps(
            {
                "dry_run": dry_run,
                **stats.as_dict(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
