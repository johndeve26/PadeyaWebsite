"""Drain pending push_events (one-shot or long-running worker).

Behavior:
  - processes pending ``push_events``
  - sends to active subscriptions (provider: log | web_push)
  - marks rows sent / failed / skipped
  - deactivates expired / high-failure subscriptions (maintenance)
  - logs batch summary counts only — never title, body, endpoints, or keys

One-shot:
  cd backend && PYTHONPATH=. python scripts/process_push_outbox.py --once

Long-running (Docker / bare invoke):
  python scripts/process_push_outbox.py
  python scripts/process_push_outbox.py --loop --maintenance
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from app.auth import models as auth_models  # noqa: F401 — User.refresh_tokens mapper
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.notifications import models as notifications_models  # noqa: F401
from app.push import models as push_models  # noqa: F401
from app.users import models as user_models  # noqa: F401
from app.notifications.settings_service import get_active_push_settings
from app.push.service import count_by_status, drain_push_outbox
from app.push.worker import run_maintenance

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [push_worker] %(message)s",
)
logger = logging.getLogger("padeya.push.worker_cli")


def _startup_banner() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        row = get_active_push_settings(db)
        provider = (row.provider if row else "log") or "log"
        enabled = bool(row.push_enabled) if row else False
    finally:
        db.close()
    logger.info(
        "push_worker starting app_env=%s push_enabled=%s provider=%s "
        "queue_enabled=%s",
        settings.app_env,
        enabled,
        provider,
        settings.push_queue_enabled,
    )
    if not enabled:
        logger.warning(
            "Push disabled in admin settings — pending rows will be skipped when drained"
        )


def run_once(*, limit: int, maintenance: bool) -> int:
    """Process one batch. Logs counts only (no payloads)."""
    db = SessionLocal()
    try:
        failed_before = count_by_status(db, "failed")
        if maintenance:
            stats = run_maintenance(db, limit=limit)
        else:
            stats = drain_push_outbox(db, limit=limit, commit=True)
        failed_after = count_by_status(db, "failed")
        # Batch summary — never log title/body/action_url/data_json/endpoints.
        logger.info(
            "push_worker batch pending_before=%s attempted=%s sent=%s "
            "failed_batch=%s skipped=%s still_pending=%s failed_total=%s "
            "deactivated_subscriptions=%s provider_mode=%s",
            stats.pending_before,
            stats.attempted,
            stats.sent,
            stats.failed,
            stats.skipped,
            stats.still_pending,
            failed_after,
            stats.deactivated_subscriptions,
            stats.provider_mode,
        )
        if failed_after > failed_before:
            logger.error(
                "push_worker new failures detected failed_total=%s "
                "(inspect /admin/push/settings deliveries — no secrets in logs)",
                failed_after,
            )
        return stats.attempted
    finally:
        db.close()


def main(argv: list[str] | None = None) -> None:
    raw = list(sys.argv[1:] if argv is None else argv)
    # Bare `python scripts/process_push_outbox.py` → long-running worker with cleanup.
    if not raw:
        raw = ["--loop", "--maintenance"]

    settings = get_settings()
    parser = argparse.ArgumentParser(description="Pàdéyá push outbox worker")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="Process one batch and exit")
    mode.add_argument("--loop", action="store_true", help="Run forever")
    parser.add_argument(
        "--limit",
        type=int,
        default=int(settings.push_worker_batch_size or 50),
    )
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=int(settings.push_worker_poll_seconds or 20),
    )
    parser.add_argument(
        "--maintenance",
        action="store_true",
        help="Deactivate expired/failed subscriptions each batch",
    )
    parser.add_argument(
        "--no-maintenance",
        action="store_true",
        help="Skip subscription cleanup",
    )
    args = parser.parse_args(raw)

    if args.no_maintenance:
        maintenance = False
    else:
        maintenance = bool(args.maintenance or args.loop)

    _startup_banner()

    if args.once:
        run_once(limit=args.limit, maintenance=maintenance)
        return

    logger.info(
        "push_worker loop poll_seconds=%s limit=%s maintenance=%s",
        args.poll_seconds,
        args.limit,
        maintenance,
    )
    cli = list(raw)
    user_set_poll = any(a.startswith("--poll") for a in cli)
    user_set_limit = any(a == "--limit" or a.startswith("--limit=") for a in cli)
    poll = max(5, int(args.poll_seconds))
    limit = max(1, int(args.limit))
    while True:
        if not user_set_poll or not user_set_limit:
            db = SessionLocal()
            try:
                from app.runtime_settings import get_runtime_setting

                if not user_set_poll:
                    poll = max(
                        5,
                        int(get_runtime_setting("push_worker_poll_seconds", db=db) or 20),
                    )
                if not user_set_limit:
                    limit = max(
                        1,
                        int(get_runtime_setting("push_worker_batch_size", db=db) or 50),
                    )
            finally:
                db.close()
        try:
            run_once(limit=limit, maintenance=maintenance)
        except Exception:  # noqa: BLE001
            logger.exception("push_worker batch error — continuing")
        time.sleep(poll)


if __name__ == "__main__":
    main()
