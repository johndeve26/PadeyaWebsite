"""Regression: maintenance section seed must commit (no Neon lock storm)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.maintenance import service as maintenance_service
from app.maintenance.models import MaintenanceSection
from app.maintenance.sections import SECTION_DEFINITIONS
from app.maintenance.service import ensure_section_rows


def test_ensure_section_rows_commits_and_short_circuits(db_session: Session):
    """Empty table must seed with commit; second call uses process short-circuit."""
    maintenance_service._SECTIONS_SEEDED = False
    db_session.execute(MaintenanceSection.__table__.delete())
    db_session.commit()

    first = ensure_section_rows(db_session)
    assert len(first) == len(SECTION_DEFINITIONS)
    assert maintenance_service._SECTIONS_SEEDED is True

    # Committed rows are visible after expire (not stuck in an open transaction).
    db_session.expire_all()
    count = db_session.scalar(select(func.count()).select_from(MaintenanceSection))
    assert int(count or 0) == len(SECTION_DEFINITIONS)

    # No pending MaintenanceSection inserts left on the session.
    pending_sections = [
        obj for obj in db_session.new if isinstance(obj, MaintenanceSection)
    ]
    assert pending_sections == []

    second = ensure_section_rows(db_session)
    assert len(second) == len(SECTION_DEFINITIONS)
    pending_after = [
        obj for obj in db_session.new if isinstance(obj, MaintenanceSection)
    ]
    assert pending_after == []


def test_ensure_section_rows_idempotent_when_already_seeded(db_session: Session):
    maintenance_service._SECTIONS_SEEDED = False
    ensure_section_rows(db_session)
    maintenance_service._SECTIONS_SEEDED = False
    again = ensure_section_rows(db_session)
    assert len(again) == len(SECTION_DEFINITIONS)
    assert maintenance_service._SECTIONS_SEEDED is True
