"""Phase 7 CC-007 — fan/host memory limit concurrent races (Postgres).

Uses direct SessionLocal workers (not concurrent TestClient) to exercise
EventMemory FOR UPDATE under real Postgres isolation.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.memories.constants import FAN_MEMORY_PHOTO_LIMIT, HOST_MEMORY_PHOTO_LIMIT
from app.memories.models import EventMemory, EventMemoryMedia
from app.memories.photos import _assert_photo_slot_available
from app.memories.service import ensure_event_memory
from tests.phase7.helpers import (
    ITERATIONS,
    seed_fan_with_ticket,
    seed_memory_event,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("PHASE45_POSTGRES") != "1",
    reason="CC-007 concurrency requires PHASE45_POSTGRES=1",
)


def _insert_active_photo(
    db: Session,
    *,
    memory_id,
    user_id,
    role: str,
) -> None:
    used = _assert_photo_slot_available(
        db,
        memory_id=memory_id,
        uploader_role=role,
        uploader_user_id=user_id if role == "fan" else None,
        limit=FAN_MEMORY_PHOTO_LIMIT if role == "fan" else HOST_MEMORY_PHOTO_LIMIT,
    )
    _ = used
    media = EventMemoryMedia(
        memory_id=memory_id,
        media_type="image",
        url=f"/media/audit/phase7/{uuid4().hex}.webp",
        storage_key=f"audit/phase7/{uuid4().hex}.webp",
        thumbnail_url=f"/media/audit/phase7/{uuid4().hex}-t.webp",
        sort_order=0,
        uploader_user_id=user_id,
        uploader_role=role,
        status="active",
        is_cover=False,
    )
    db.add(media)
    db.commit()


def _active_count(
    db: Session, *, memory_id, role: str, user_id=None
) -> int:
    q = (
        select(func.count())
        .select_from(EventMemoryMedia)
        .where(
            EventMemoryMedia.memory_id == memory_id,
            EventMemoryMedia.uploader_role == role,
            EventMemoryMedia.status == "active",
        )
    )
    if user_id is not None:
        q = q.where(EventMemoryMedia.uploader_user_id == user_id)
    return int(db.scalar(q) or 0)


def test_cc007_fan_limit_concurrent_race(client: TestClient, db_session: Session):
    _ = client
    _, _, event = seed_memory_event(db_session)
    fan, _ = seed_fan_with_ticket(db_session, event)
    memory = ensure_event_memory(db_session, event)
    db_session.commit()
    memory_id = memory.id
    fan_id = fan.id
    SessionLocal = sessionmaker(
        bind=db_session.get_bind(), autocommit=False, autoflush=False
    )
    workers = FAN_MEMORY_PHOTO_LIMIT + 4
    bad_iters = 0

    for _ in range(ITERATIONS):
        db_session.query(EventMemoryMedia).filter(
            EventMemoryMedia.memory_id == memory_id
        ).delete()
        db_session.commit()

        def worker() -> str:
            s = SessionLocal()
            try:
                _insert_active_photo(
                    s, memory_id=memory_id, user_id=fan_id, role="fan"
                )
                return "ok"
            except HTTPException:
                s.rollback()
                return "limit"
            except Exception as exc:  # noqa: BLE001
                s.rollback()
                return f"err:{type(exc).__name__}"
            finally:
                s.close()

        results: list[str] = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = [pool.submit(worker) for _ in range(workers)]
            for fut in as_completed(futs):
                results.append(fut.result())

        db_session.expire_all()
        count = _active_count(
            db_session, memory_id=memory_id, role="fan", user_id=fan_id
        )
        ok = results.count("ok")
        if count > FAN_MEMORY_PHOTO_LIMIT or ok > FAN_MEMORY_PHOTO_LIMIT:
            bad_iters += 1

    assert bad_iters == 0, f"CC-007 fan limit violated in {bad_iters}/{ITERATIONS}"


def test_cc007_host_limit_concurrent_race(client: TestClient, db_session: Session):
    _ = client
    _, host_user, event = seed_memory_event(db_session)
    memory = ensure_event_memory(db_session, event)
    db_session.commit()
    memory_id = memory.id
    host_id = host_user.id
    SessionLocal = sessionmaker(
        bind=db_session.get_bind(), autocommit=False, autoflush=False
    )
    workers = HOST_MEMORY_PHOTO_LIMIT + 4
    bad_iters = 0

    for _ in range(ITERATIONS):
        db_session.query(EventMemoryMedia).filter(
            EventMemoryMedia.memory_id == memory_id
        ).delete()
        db_session.commit()

        def worker() -> str:
            s = SessionLocal()
            try:
                _insert_active_photo(
                    s, memory_id=memory_id, user_id=host_id, role="host"
                )
                return "ok"
            except HTTPException:
                s.rollback()
                return "limit"
            except Exception as exc:  # noqa: BLE001
                s.rollback()
                return f"err:{type(exc).__name__}"
            finally:
                s.close()

        results: list[str] = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = [pool.submit(worker) for _ in range(workers)]
            for fut in as_completed(futs):
                results.append(fut.result())

        db_session.expire_all()
        count = _active_count(db_session, memory_id=memory_id, role="host")
        ok = results.count("ok")
        if count > HOST_MEMORY_PHOTO_LIMIT or ok > HOST_MEMORY_PHOTO_LIMIT:
            bad_iters += 1

    assert bad_iters == 0, f"Host limit violated in {bad_iters}/{ITERATIONS}"
