"""Permission catalog completeness and role wiring."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.users.constants import (
    DEFAULT_PERMISSIONS,
    PERMISSION_IMPLIES,
    REQUIRED_PERMISSION_CODES,
    ROLE_PERMISSIONS,
)
from app.users.models import Permission
from app.users.service import get_role_by_name, user_has_permission


def test_required_permission_codes_are_seeded(db_session: Session):
    seeded = {code for (code, _) in DEFAULT_PERMISSIONS}
    missing_from_catalog = REQUIRED_PERMISSION_CODES - seeded
    assert not missing_from_catalog, f"Missing from DEFAULT_PERMISSIONS: {missing_from_catalog}"

    db_codes = set(db_session.scalars(select(Permission.code)).all())
    missing_from_db = REQUIRED_PERMISSION_CODES - db_codes
    assert not missing_from_db, f"Missing from DB seed: {missing_from_db}"


def test_role_permission_codes_exist_in_catalog():
    catalog = {code for (code, _) in DEFAULT_PERMISSIONS}
    for role_name, codes in ROLE_PERMISSIONS.items():
        unknown = set(codes) - catalog
        assert not unknown, f"{role_name} references unknown permissions: {unknown}"


def test_finance_cannot_mark_payouts_paid(db_session: Session):
    role = get_role_by_name(db_session, "finance_admin")
    assert role is not None
    codes = {p.code for p in role.permissions}
    assert "payouts.review" in codes
    assert "payouts.approve" in codes
    assert "payouts.reject" in codes
    assert "payouts.mark_paid" not in codes


def test_buyer_has_self_service_ticket_and_support_perms(db_session: Session):
    role = get_role_by_name(db_session, "buyer")
    assert role is not None
    codes = {p.code for p in role.permissions}
    for code in (
        "tickets.read_own",
        "tickets.transfer",
        "tickets.cancel",
        "tickets.reissue_qr",
        "reviews.create",
        "refunds.create",
        "support.create",
    ):
        assert code in codes, code


def test_merch_role_permission_matrix(db_session: Session):
    host = get_role_by_name(db_session, "host")
    staff = get_role_by_name(db_session, "host_staff")
    support = get_role_by_name(db_session, "support_agent")
    assert host is not None and staff is not None and support is not None

    host_codes = {p.code for p in host.permissions}
    staff_codes = {p.code for p in staff.permissions}
    support_codes = {p.code for p in support.permissions}

    assert "merch.manage_own" in host_codes
    assert "merch.fulfill" in host_codes
    assert "merch.manage_own" not in staff_codes
    assert "merch.fulfill" in staff_codes
    assert "merch.view_fulfillment" in staff_codes
    assert "merch.view_admin" in support_codes
    assert "merch.moderate" not in support_codes
    assert "payments.view" not in support_codes
    assert "refunds.approve" not in support_codes


def test_events_manage_own_implies_granular():
    class _Perm:
        def __init__(self, code: str) -> None:
            self.code = code

    class _Role:
        name = "host"
        permissions = [_Perm("events.manage_own")]

    class _User:
        roles = [_Role()]

    user = _User()
    assert user_has_permission(user, "events.manage_own")  # type: ignore[arg-type]
    assert user_has_permission(user, "events.update_own")  # type: ignore[arg-type]
    assert user_has_permission(user, "events.archive_own")  # type: ignore[arg-type]
    assert user_has_permission(user, "ticket_types.deactivate")  # type: ignore[arg-type]
    assert not user_has_permission(user, "events.approve")  # type: ignore[arg-type]


def test_permission_implies_map_is_consistent():
    catalog = {code for (code, _) in DEFAULT_PERMISSIONS}
    for umbrella, implied in PERMISSION_IMPLIES.items():
        assert umbrella in catalog, umbrella
        missing = implied - catalog
        assert not missing, f"{umbrella} implies unknown: {missing}"
