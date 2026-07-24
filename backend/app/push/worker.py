"""Push outbox drain helpers (used by CLI worker + optional in-process sweeper).

Never log notification title/body, endpoints, or VAPID material.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.push.service import DrainStats, cleanup_failed_subscriptions, drain_push_outbox

logger = logging.getLogger("padeya.push.worker")


def process_pending_push(
    db: Session, *, limit: int = 50, commit: bool = True
) -> int:
    return drain_push_outbox(db, limit=limit, commit=commit).attempted


def run_maintenance(db: Session, *, limit: int = 50) -> DrainStats:
    """Drain pending events, then deactivate expired/failed subscriptions."""
    stats = drain_push_outbox(db, limit=limit, commit=False)
    cleaned = cleanup_failed_subscriptions(db)
    db.commit()
    if cleaned:
        logger.info("push cleanup deactivated_subscriptions=%s", cleaned)
    return DrainStats(
        pending_before=stats.pending_before,
        attempted=stats.attempted,
        sent=stats.sent,
        failed=stats.failed,
        skipped=stats.skipped,
        still_pending=stats.still_pending,
        provider_mode=stats.provider_mode,
        deactivated_subscriptions=cleaned,
    )
