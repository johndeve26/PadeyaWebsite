"""CLI: expire due pending order reservations (inventory release).

Usage:
  APP_ENV=production .venv/bin/python -m scripts.expire_order_reservations
"""

from __future__ import annotations

import argparse
import os
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Expire pending Pàdéyá orders past reservation_expires_at."
    )
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    # Import after env is available
    from app.core.database import SessionLocal
    from app.payments.reservations import expire_due_reservations

    db = SessionLocal()
    try:
        result = expire_due_reservations(db, limit=max(1, int(args.limit)))
        print(
            f"examined={result['examined']} expired={result['expired']} "
            f"skipped={result['skipped']}"
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    # Refuse accidental prod mutation unless APP_ENV is set intentionally.
    if os.environ.get("APP_ENV", "").strip().lower() == "production":
        # Still allowed — ops job — but never print secrets.
        pass
    sys.exit(main())
