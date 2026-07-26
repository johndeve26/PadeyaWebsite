"""Safe, optional migration of legacy local media into Cloudflare R2.

Usage (from backend/):
  PYTHONPATH=. python scripts/migrate_media_to_r2.py --dry-run
  PYTHONPATH=. python scripts/migrate_media_to_r2.py --public-only --feature events
  PYTHONPATH=. python scripts/migrate_media_to_r2.py --private-only --feature support

Never runs automatically. Idempotent / restartable.
Never migrates private files into padeya-media.
Never prints credentials.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.media import media_storage_provider, storage_key_from_url
from app.core.media_private import get_private_media_storage, is_public_padeya_media_url
from app.core.r2_client import IMMUTABLE_PUBLIC_CACHE_CONTROL
from app.events.models import EventMedia
from app.memories.models import EventMemoryMedia
from app.support.models import SupportTicketAttachment


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Migrate legacy media to R2 (manual).")
    p.add_argument("--dry-run", action="store_true", help="Report only; no writes")
    p.add_argument("--public-only", action="store_true")
    p.add_argument("--private-only", action="store_true")
    p.add_argument(
        "--feature",
        action="append",
        choices=["events", "memories", "support", "all"],
        default=[],
        help="Feature scope (repeatable). Default: all selected class.",
    )
    p.add_argument("--limit", type=int, default=200)
    return p.parse_args()


def _local_public_path(key: str) -> Path | None:
    settings = get_settings()
    root = Path(settings.media_root)
    path = root / key
    return path if path.is_file() else None


def _migrate_public_row(
    *,
    url: str,
    storage_key: str | None,
    dry_run: bool,
) -> str:
    if is_public_padeya_media_url(url) and "media.padeya.com" in (url or ""):
        return "skip-already-r2"
    key = storage_key or storage_key_from_url(url)
    if not key:
        return "skip-no-key"
    path = _local_public_path(key)
    if path is None:
        return "skip-missing-local"
    if dry_run:
        return "dry-run-would-upload-public"
    from app.core.media import get_public_media_storage

    data = path.read_bytes()
    # Upload under the same key by using store then... our store generates new UUID keys.
    # For migration we put_object with the existing key via the R2 client.
    from app.core.r2_client import R2BucketClient, public_r2_config

    client = R2BucketClient(public_r2_config())
    ctype = "image/webp" if key.endswith(".webp") else "application/octet-stream"
    if key.endswith(".png"):
        ctype = "image/png"
    elif key.endswith(".jpg") or key.endswith(".jpeg"):
        ctype = "image/jpeg"
    client.put_object(
        key=key,
        data=data,
        content_type=ctype,
        cache_control=IMMUTABLE_PUBLIC_CACHE_CONTROL,
    )
    if not client.head_object(key):
        return "error-verify-failed"
    return "uploaded-public"


def migrate_events(*, dry_run: bool, limit: int) -> dict[str, int]:
    from app.core.media import get_public_media_storage

    stats: dict[str, int] = {}
    db = SessionLocal()
    try:
        rows = db.scalars(select(EventMedia).limit(limit)).all()
        for row in rows:
            result = _migrate_public_row(
                url=row.url, storage_key=None, dry_run=dry_run
            )
            stats[result] = stats.get(result, 0) + 1
            if result == "uploaded-public" and not dry_run:
                key = storage_key_from_url(row.url)
                if key:
                    public = get_public_media_storage()
                    # Point URL at public CDN while keeping the same object key.
                    settings = get_settings()
                    base = (settings.r2_public_url or "").rstrip("/")
                    row.url = f"{base}/{key}"
        if not dry_run:
            db.commit()
    finally:
        db.close()
    return stats


def migrate_memories(*, dry_run: bool, limit: int) -> dict[str, int]:
    stats: dict[str, int] = {}
    db = SessionLocal()
    try:
        rows = db.scalars(select(EventMemoryMedia).limit(limit)).all()
        settings = get_settings()
        base = (settings.r2_public_url or "").rstrip("/")
        for row in rows:
            result = _migrate_public_row(
                url=row.url, storage_key=row.storage_key, dry_run=dry_run
            )
            stats[result] = stats.get(result, 0) + 1
            if result == "uploaded-public" and not dry_run and row.storage_key:
                row.url = f"{base}/{row.storage_key}"
                if row.thumbnail_url and not is_public_padeya_media_url(row.thumbnail_url):
                    thumb_key = storage_key_from_url(row.thumbnail_url)
                    if thumb_key:
                        _migrate_public_row(
                            url=row.thumbnail_url,
                            storage_key=thumb_key,
                            dry_run=False,
                        )
                        row.thumbnail_url = f"{base}/{thumb_key}"
        if not dry_run:
            db.commit()
    finally:
        db.close()
    return stats


def migrate_support(*, dry_run: bool, limit: int) -> dict[str, int]:
    stats: dict[str, int] = {}
    db = SessionLocal()
    try:
        rows = db.scalars(
            select(SupportTicketAttachment)
            .where(SupportTicketAttachment.deleted_at.is_(None))
            .limit(limit)
        ).all()
        private = get_private_media_storage()
        legacy_root = Path("storage/support_attachments")
        for row in rows:
            key = row.storage_key or ""
            if key.startswith("support/") and private.exists(key):
                stats["skip-already-private"] = stats.get("skip-already-private", 0) + 1
                continue
            path = legacy_root / key
            if not path.is_file():
                stats["skip-missing-local"] = stats.get("skip-missing-local", 0) + 1
                continue
            if dry_run:
                stats["dry-run-would-upload-private"] = (
                    stats.get("dry-run-would-upload-private", 0) + 1
                )
                continue
            data = path.read_bytes()
            # Never send to public bucket.
            stored = private.store_validated_bytes(
                data=data,
                folder=f"support/{row.case_id}/attachments",
                extension=Path(row.filename or "bin").suffix or ".bin",
                content_type=row.content_type or "application/octet-stream",
                max_bytes=max(len(data), 1),
                filename=row.filename or "upload.bin",
            )
            if not private.exists(stored.key):
                stats["error-verify-failed"] = stats.get("error-verify-failed", 0) + 1
                continue
            row.storage_key = stored.key
            stats["uploaded-private"] = stats.get("uploaded-private", 0) + 1
        if not dry_run:
            db.commit()
    finally:
        db.close()
    return stats


def main() -> int:
    args = _parse_args()
    if media_storage_provider() != "r2" and not args.dry_run:
        print("MEDIA_STORAGE_PROVIDER must be r2 for non-dry-run migration.")
        return 1
    if args.public_only and args.private_only:
        print("Choose at most one of --public-only / --private-only")
        return 1

    features = args.feature or ["all"]
    if "all" in features:
        features = ["events", "memories", "support"]

    do_public = not args.private_only
    do_private = not args.public_only

    summary: dict[str, dict[str, int]] = {}
    if do_public and "events" in features:
        summary["events"] = migrate_events(dry_run=args.dry_run, limit=args.limit)
    if do_public and "memories" in features:
        summary["memories"] = migrate_memories(dry_run=args.dry_run, limit=args.limit)
    if do_private and "support" in features:
        summary["support"] = migrate_support(dry_run=args.dry_run, limit=args.limit)

    print({"dry_run": args.dry_run, "results": summary})
    return 0


if __name__ == "__main__":
    sys.exit(main())
