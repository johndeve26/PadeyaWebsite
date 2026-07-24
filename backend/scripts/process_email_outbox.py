"""Drain pending email_events (one-shot or long-running worker).

One-shot (cron / manual):
  cd backend && PYTHONPATH=. python scripts/process_email_outbox.py --once

Long-running Docker worker:
  python scripts/process_email_outbox.py --loop

Never logs SMTP passwords or full email bodies in production.
"""

from __future__ import annotations

import argparse
import logging
import time

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.email.config import assert_email_runtime_safe, email_runtime, provider_mode_label
from app.email.queue import count_by_status, drain_email_outbox

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [email_worker] %(message)s",
)
logger = logging.getLogger("padeya.email.worker")


def _startup_banner() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        cfg = email_runtime(settings, db=db)
        mode = provider_mode_label(settings, db=db)
    finally:
        db.close()
    logger.info(
        "email_worker starting app_env=%s enabled=%s provider_mode=%s "
        "queue_enabled=%s smtp_host_set=%s from=%s",
        settings.app_env,
        cfg.enabled,
        mode,
        cfg.queue_enabled,
        bool(cfg.smtp_host),
        cfg.from_email,
    )
    # Never log username/password.
    if not cfg.enabled:
        logger.warning(
            "EMAIL_ENABLED=false — pending rows will be marked skipped when drained"
        )


def _validate_or_warn(*, db) -> None:
    """Log loud misconfig; do not exit — admin may fix SMTP in the dashboard without restart."""
    try:
        assert_email_runtime_safe(db=db)
    except RuntimeError as exc:
        logger.error(
            "Email configuration invalid: %s — "
            "fix SMTP under Admin → Email settings (worker keeps polling)",
            exc,
        )


def run_once(*, limit: int) -> int:
    db = SessionLocal()
    try:
        _validate_or_warn(db=db)
        failed_before = count_by_status(db, "failed")
        stats = drain_email_outbox(db, limit=limit, commit=True)
        failed_after = count_by_status(db, "failed")
        logger.info(
            "email_worker batch pending_before=%s attempted=%s sent=%s "
            "failed_batch=%s skipped=%s still_pending=%s failed_total=%s "
            "provider_mode=%s",
            stats.pending_before,
            stats.attempted,
            stats.sent,
            stats.failed,
            stats.skipped,
            stats.still_pending,
            failed_after,
            stats.provider_mode,
        )
        if failed_after > failed_before:
            logger.error(
                "email_worker new failures detected failed_total=%s "
                "(inspect /admin/emails or SQL — bodies omitted from logs)",
                failed_after,
            )
        return stats.attempted
    finally:
        db.close()


def main(argv: list[str] | None = None) -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Pàdéyá email outbox worker")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--once",
        action="store_true",
        help="Process one batch and exit (default when not --loop)",
    )
    mode.add_argument(
        "--loop",
        action="store_true",
        help="Run forever, polling for pending email_events",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=int(settings.email_worker_batch_size or 50),
        help="Max events per batch",
    )
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=int(settings.email_worker_poll_seconds or 20),
        help="Sleep between batches in --loop mode",
    )
    args = parser.parse_args(argv)

    _startup_banner()

    loop = bool(args.loop)
    if not loop and not args.once:
        # Default one-shot for cron compatibility
        loop = False

    if not loop:
        n = run_once(limit=max(1, args.limit))
        print(f"processed={n}")
        return

    poll = max(5, int(args.poll_seconds))
    limit = max(1, int(args.limit))
    # Re-resolve poll/batch from DB each iteration unless CLI explicitly set.
    cli = list(argv if argv is not None else [])
    user_set_poll = any(a.startswith("--poll") for a in cli)
    user_set_limit = any(a == "--limit" or a.startswith("--limit=") for a in cli)
    logger.info("email_worker loop mode poll_seconds=%s batch_limit=%s", poll, limit)
    while True:
        if not user_set_poll or not user_set_limit:
            db = SessionLocal()
            try:
                from app.runtime_settings import get_runtime_setting

                if not user_set_poll:
                    poll = max(
                        5,
                        int(
                            get_runtime_setting("email_worker_poll_seconds", db=db) or 20
                        ),
                    )
                if not user_set_limit:
                    limit = max(
                        1,
                        int(
                            get_runtime_setting("email_worker_batch_size", db=db) or 50
                        ),
                    )
            finally:
                db.close()
        try:
            run_once(limit=limit)
        except Exception:  # noqa: BLE001 — keep worker alive; log without secrets
            logger.exception(
                "email_worker batch failed — will retry after poll "
                "(credentials and bodies are never logged)"
            )
        time.sleep(poll)


if __name__ == "__main__":
    main()
