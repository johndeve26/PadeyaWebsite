"""CLI: expire due pending order reservations (inventory release).

One-shot (cron / manual):
  cd backend && PYTHONPATH=. python scripts/expire_order_reservations.py --once

Long-running Docker worker:
  python scripts/expire_order_reservations.py --loop

Never logs secrets or customer PII.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [reservation_sweeper] %(message)s",
)
logger = logging.getLogger("padeya.reservation_sweeper")


def run_once(*, limit: int) -> dict[str, int]:
    # Ensure SQLAlchemy relationship targets (Ticket, Host, …) are registered.
    import app.main  # noqa: F401
    from app.core.database import SessionLocal
    from app.payments.reservations import expire_due_reservations

    db = SessionLocal()
    try:
        result = expire_due_reservations(db, limit=max(1, int(limit)))
        logger.info(
            "reservation_sweeper batch examined=%s expired=%s skipped=%s",
            result["examined"],
            result["expired"],
            result["skipped"],
        )
        return result
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Expire pending Pàdéyá orders past reservation_expires_at."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--once",
        action="store_true",
        help="Process one batch and exit (default when not --loop)",
    )
    mode.add_argument(
        "--loop",
        action="store_true",
        help="Run forever, polling for due reservations",
    )
    parser.add_argument("--limit", type=int, default=100, help="Max orders per batch")
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=int(os.environ.get("RESERVATION_SWEEPER_POLL_SECONDS", "60")),
        help="Sleep between batches in --loop mode",
    )
    args = parser.parse_args(argv)

    loop = bool(args.loop)
    if not loop and not args.once:
        loop = False

    if not loop:
        result = run_once(limit=max(1, int(args.limit)))
        print(
            f"examined={result['examined']} expired={result['expired']} "
            f"skipped={result['skipped']}"
        )
        return 0

    poll = max(15, int(args.poll_seconds))
    limit = max(1, int(args.limit))
    logger.info("reservation_sweeper loop mode poll_seconds=%s batch_limit=%s", poll, limit)
    while True:
        try:
            run_once(limit=limit)
        except Exception:  # noqa: BLE001 — keep worker alive
            logger.exception("reservation_sweeper batch failed — will retry after poll")
        time.sleep(poll)


if __name__ == "__main__":
    sys.exit(main())
