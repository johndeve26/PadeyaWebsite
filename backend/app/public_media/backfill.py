"""Controlled legacy public-media backfill (dry-run / resume).

Usage (from backend/):
  python -m app.public_media.backfill --dry-run --limit 50
  python -m app.public_media.backfill --limit 50 --cursor <asset-or-url>
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.media import get_public_media_storage, storage_key_from_url
from app.public_media.processor import PublicMediaProcessingError
from app.public_media.roles import MediaRole
from app.public_media.service import process_and_store_public_media, public_media_response

logger = logging.getLogger(__name__)


@dataclass
class BackfillReport:
    scanned: int = 0
    already_migrated: int = 0
    processed: int = 0
    failed: int = 0
    unsupported: int = 0
    missing_source: int = 0
    bytes_before: int = 0
    bytes_after: int = 0
    failures: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "scanned": self.scanned,
            "already_migrated": self.already_migrated,
            "processed": self.processed,
            "failed": self.failed,
            "unsupported": self.unsupported,
            "missing_source": self.missing_source,
            "bytes_before": self.bytes_before,
            "bytes_after": self.bytes_after,
            "estimated_reduction_ratio": (
                round(1 - (self.bytes_after / self.bytes_before), 4)
                if self.bytes_before
                else None
            ),
            "failure_count": len(self.failures),
        }


def _is_storage_origin(url: str | None) -> bool:
    if not url:
        return False
    if url.startswith("/media/"):
        return True
    key = storage_key_from_url(url)
    return bool(key)


def _read_source_bytes(url: str) -> bytes | None:
    key = storage_key_from_url(url)
    if not key:
        return None
    storage = get_public_media_storage()
    # Local and R2 storages differ; prefer local path when available.
    root = getattr(storage, "_root", None)
    if callable(root):
        path = root() / key
        if path.is_file():
            return path.read_bytes()
    # R2: best-effort via public URL fetch is intentionally avoided for
    # arbitrary remotes. Only same-origin /media keys are supported here.
    if url.startswith("/media/"):
        return None
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https"} and "padeya" in (parsed.hostname or ""):
        try:
            import urllib.request

            with urllib.request.urlopen(url, timeout=20) as resp:  # noqa: S310
                data = resp.read(12 * 1024 * 1024)
                return data
        except Exception:
            return None
    return None


def backfill_event_banners(
    db: Session,
    *,
    limit: int = 50,
    dry_run: bool = True,
    report: BackfillReport | None = None,
) -> BackfillReport:
    from app.events.models import Event

    report = report or BackfillReport()
    q = (
        db.query(Event)
        .filter(Event.banner_url.isnot(None))
        .order_by(Event.created_at.asc())
        .limit(limit)
    )
    for event in q.all():
        report.scanned += 1
        if getattr(event, "banner_media", None):
            report.already_migrated += 1
            continue
        url = event.banner_url
        if not _is_storage_origin(url):
            report.unsupported += 1
            continue
        raw = _read_source_bytes(url or "")
        if not raw:
            report.missing_source += 1
            continue
        report.bytes_before += len(raw)
        if dry_run:
            report.processed += 1
            continue
        try:
            payload = process_and_store_public_media(
                db,
                data=raw,
                declared_content_type=None,
                role=MediaRole.EVENT_COVER,
                owner_type="event",
                owner_id=event.id,
                store_source=True,
            )
            public = public_media_response(payload)
            event.banner_url = public.get("display_url") or event.banner_url
            event.banner_media = public
            sizes = payload.get("_variant_byte_sizes") or {}
            report.bytes_after += sum(int(v) for v in sizes.values())
            report.processed += 1
            db.commit()
        except (PublicMediaProcessingError, Exception) as exc:
            db.rollback()
            report.failed += 1
            report.failures.append(f"event:{event.id}:{exc.__class__.__name__}")
            logger.warning("backfill_event_banner_failed id=%s", event.id, exc_info=True)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill public media variants")
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    db = SessionLocal()
    try:
        report = backfill_event_banners(
            db, limit=args.limit, dry_run=args.dry_run
        )
        print(report.as_dict())
        return 0 if report.failed == 0 else 2
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
