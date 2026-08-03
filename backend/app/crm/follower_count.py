"""Live host follower counts (excludes host owner self-follows)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crm.models import HostFollower
from app.hosts.models import Host
from app.legacy.models import HostLegacyScore


def count_host_followers(db: Session, host_id: UUID) -> int:
    """Count `host_followers` rows for a host, excluding the host owner."""
    host = db.get(Host, host_id)
    stmt = (
        select(func.count())
        .select_from(HostFollower)
        .where(HostFollower.host_id == host_id)
    )
    if host is not None:
        stmt = stmt.where(HostFollower.user_id != host.user_id)
    return int(db.scalar(stmt) or 0)


def follower_counts_by_host(
    db: Session, host_ids: list[UUID]
) -> dict[UUID, int]:
    """Batch live follower counts for discover / list surfaces."""
    if not host_ids:
        return {}
    hosts = {
        h.id: h
        for h in db.scalars(select(Host).where(Host.id.in_(host_ids))).all()
    }
    rows = db.execute(
        select(HostFollower.host_id, HostFollower.user_id).where(
            HostFollower.host_id.in_(host_ids)
        )
    ).all()
    counts: dict[UUID, int] = {hid: 0 for hid in host_ids}
    for host_id, user_id in rows:
        host = hosts.get(host_id)
        if host is not None and user_id == host.user_id:
            continue
        counts[host_id] = counts.get(host_id, 0) + 1
    return counts


def sync_legacy_follower_count(db: Session, host_id: UUID) -> int:
    """Keep denormalized `HostLegacyScore.followers` aligned with live rows.

    Does not recompute composite score. Does not commit.
    """
    count = count_host_followers(db, host_id)
    score = db.scalar(
        select(HostLegacyScore).where(HostLegacyScore.host_id == host_id)
    )
    if score is not None and int(score.followers) != count:
        score.followers = count
    return count
