"""§10 Host team invite methods — email + username checklist."""

from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.email.models import EmailEvent
from app.hosts.models import HostTeamAuditLog, HostTeamInvite
from app.messaging.models import InAppNotification
from app.passport.privacy import VISIBILITY_PUBLIC
from app.passport.service import ensure_passport
from app.users.models import User


def _auth(client: TestClient, email: str, name: str = "User") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _onboard(client: TestClient, headers: dict[str, str], name: str) -> dict:
    r = client.post(
        "/api/v1/hosts/onboard",
        headers=headers,
        json={
            "display_name": name,
            "bio": "Invite methods host",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _invite_token(db: Session, email: str) -> str:
    email_row = db.scalar(
        select(EmailEvent)
        .where(
            EmailEvent.recipient_email == email,
            EmailEvent.template == "team_invite",
        )
        .order_by(EmailEvent.created_at.desc())
    )
    assert email_row is not None
    path = (email_row.context_json or {})["invite_path"]
    return path.rsplit("/", 1)[-1]


def _set_username(db: Session, user: User, username: str) -> None:
    passport = ensure_passport(db, user)
    passport.username = username
    passport.display_name = user.full_name or username
    passport.visibility = VISIBILITY_PUBLIC
    db.commit()


def test_host_can_invite_by_email(client: TestClient, db_session: Session):
    host_h = _auth(client, "m10-email-host@example.com", "M10 Email Host")
    _onboard(client, host_h, "M10 Email Host Co")

    created = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"invite_identifier": "m10-new@example.com", "role": "scanner"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["invite_method"] == "email"
    assert body["status"] == "pending"
    assert body["masked_email"]
    assert "m10-new@example.com" not in body["masked_email"]


def test_host_can_invite_unknown_email(client: TestClient, db_session: Session):
    host_h = _auth(client, "m10-unknown-host@example.com", "M10 Unknown Host")
    _onboard(client, host_h, "M10 Unknown Host Co")

    created = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"invite_identifier": "m10-nobody-yet@example.com", "role": "viewer"},
    )
    assert created.status_code == 201, created.text
    invite_id = UUID(created.json()["invite_id"])
    row = db_session.get(HostTeamInvite, invite_id)
    assert row is not None
    assert row.invite_method == "email"
    assert row.invited_user_id is None
    assert row.email == "m10-nobody-yet@example.com"
    assert row.status == "pending"


def test_host_can_invite_existing_user_by_email(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "m10-known-host@example.com", "M10 Known Host")
    _onboard(client, host_h, "M10 Known Host Co")
    _auth(client, "m10-known-member@example.com", "Known Member")
    member = db_session.scalar(
        select(User).where(User.email == "m10-known-member@example.com")
    )
    assert member is not None

    created = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={
            "invite_identifier": "m10-known-member@example.com",
            "role": "scanner",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["invite_method"] == "email"
    row = db_session.get(HostTeamInvite, UUID(created.json()["invite_id"]))
    assert row is not None
    assert row.invited_user_id == member.id


def test_host_can_invite_existing_user_by_username(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "m10-uname-host@example.com", "M10 Uname Host")
    _onboard(client, host_h, "M10 Uname Host Co")
    _auth(client, "m10-uname-member@example.com", "Uname Member")
    member = db_session.scalar(
        select(User).where(User.email == "m10-uname-member@example.com")
    )
    assert member is not None
    _set_username(db_session, member, "m10_gate")

    created = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"invite_identifier": "m10_gate", "role": "scanner"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["invite_method"] == "username"
    assert body["username"] == "@m10_gate"
    assert body["status"] == "pending"


def test_username_invite_stores_invited_user_id(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "m10-store-host@example.com", "M10 Store Host")
    _onboard(client, host_h, "M10 Store Host Co")
    _auth(client, "m10-store-member@example.com", "Store Member")
    member = db_session.scalar(
        select(User).where(User.email == "m10-store-member@example.com")
    )
    assert member is not None
    _set_username(db_session, member, "m10_store")

    created = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"invite_identifier": "@m10_store", "role": "viewer"},
    )
    assert created.status_code == 201, created.text
    row = db_session.get(HostTeamInvite, UUID(created.json()["invite_id"]))
    assert row is not None
    assert row.invited_user_id == member.id
    assert row.invited_username == "m10_store"
    assert row.invite_method == "username"
    # Delivery email kept internally
    assert row.email == "m10-store-member@example.com"


def test_username_invite_does_not_expose_private_email(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "m10-priv-host@example.com", "M10 Priv Host")
    host = _onboard(client, host_h, "M10 Priv Host Co")
    _auth(client, "m10-priv-member@example.com", "Priv Member")
    member = db_session.scalar(
        select(User).where(User.email == "m10-priv-member@example.com")
    )
    assert member is not None
    _set_username(db_session, member, "m10_priv")

    created = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"invite_identifier": "@m10_priv", "role": "viewer"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body.get("masked_email") is None
    assert "m10-priv-member@example.com" not in created.text
    assert "invited_email" not in body

    listed = client.get(
        f"/api/v1/host/team/invites?host_id={host['id']}",
        headers=host_h,
    )
    assert listed.status_code == 200, listed.text
    rows = listed.json()
    assert isinstance(rows, list)
    match = next(
        (
            r
            for r in rows
            if r.get("id") == body["invite_id"]
            or r.get("invited_username") == "@m10_priv"
        ),
        None,
    )
    assert match is not None
    assert match.get("invite_method") == "username"
    assert match.get("invited_username") == "@m10_priv"
    assert match.get("invited_email") is None
    assert "m10-priv-member@example.com" not in str(match)


def test_unknown_username_invite_fails_cleanly(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "m10-miss-host@example.com", "M10 Miss Host")
    _onboard(client, host_h, "M10 Miss Host Co")

    missing = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"invite_identifier": "@no_such_m10_user", "role": "viewer"},
    )
    assert missing.status_code == 404
    assert missing.json()["detail"] == "No Pàdéyá user found with that username."
    assert (
        db_session.scalar(
            select(HostTeamInvite).where(
                HostTeamInvite.invited_username == "no_such_m10_user"
            )
        )
        is None
    )


def test_username_with_at_normalizes_correctly(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "m10-norm-host@example.com", "M10 Norm Host")
    _onboard(client, host_h, "M10 Norm Host Co")
    _auth(client, "m10-norm-member@example.com", "Norm Member")
    member = db_session.scalar(
        select(User).where(User.email == "m10-norm-member@example.com")
    )
    assert member is not None
    _set_username(db_session, member, "m10_norm")

    with_at = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"invite_identifier": "@M10_Norm", "role": "viewer"},
    )
    assert with_at.status_code == 201, with_at.text
    assert with_at.json()["username"] == "@m10_norm"
    row = db_session.get(HostTeamInvite, UUID(with_at.json()["invite_id"]))
    assert row is not None
    assert row.invited_username == "m10_norm"


def test_duplicate_username_invite_is_prevented(
    client: TestClient, db_session: Session
):
    """Only one pending invite per username/user — second invite replaces, not duplicates."""
    host_h = _auth(client, "m10-dup-host@example.com", "M10 Dup Host")
    _onboard(client, host_h, "M10 Dup Host Co")
    _auth(client, "m10-dup-member@example.com", "Dup Member")
    member = db_session.scalar(
        select(User).where(User.email == "m10-dup-member@example.com")
    )
    assert member is not None
    _set_username(db_session, member, "m10_dup")

    first = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"invite_identifier": "@m10_dup", "role": "scanner"},
    )
    assert first.status_code == 201, first.text
    first_id = first.json()["invite_id"]

    second = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"invite_identifier": "m10_dup", "role": "admin"},
    )
    assert second.status_code == 201, second.text
    assert second.json()["invite_id"] == first_id

    pending = list(
        db_session.scalars(
            select(HostTeamInvite).where(
                HostTeamInvite.invited_user_id == member.id,
                HostTeamInvite.status == "pending",
            )
        )
    )
    assert len(pending) == 1


def test_invited_user_can_accept_username_invite(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "m10-accept-host@example.com", "M10 Accept Host")
    _onboard(client, host_h, "M10 Accept Host Co")
    member_h = _auth(client, "m10-accept-member@example.com", "Accept Member")
    member = db_session.scalar(
        select(User).where(User.email == "m10-accept-member@example.com")
    )
    assert member is not None
    _set_username(db_session, member, "m10_accept")

    created = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"invite_identifier": "@m10_accept", "role": "scanner"},
    )
    assert created.status_code == 201
    token = _invite_token(db_session, "m10-accept-member@example.com")

    accepted = client.post(
        f"/api/v1/team/invites/{token}/accept",
        headers=member_h,
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "active"
    assert accepted.json()["user_id"] == str(member.id)


def test_different_user_cannot_accept_username_invite(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "m10-wrong-host@example.com", "M10 Wrong Host")
    _onboard(client, host_h, "M10 Wrong Host Co")
    _auth(client, "m10-wrong-target@example.com", "Target Member")
    target = db_session.scalar(
        select(User).where(User.email == "m10-wrong-target@example.com")
    )
    assert target is not None
    _set_username(db_session, target, "m10_wrong_target")

    created = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"invite_identifier": "@m10_wrong_target", "role": "viewer"},
    )
    assert created.status_code == 201
    token = _invite_token(db_session, "m10-wrong-target@example.com")

    other_h = _auth(client, "m10-wrong-other@example.com", "Other")
    denied = client.post(
        f"/api/v1/team/invites/{token}/accept",
        headers=other_h,
    )
    assert denied.status_code == 403
    assert (
        denied.json()["detail"]
        == "This invite was sent to another Pàdéyá account."
    )


def test_email_invite_still_requires_matching_email(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "m10-match-host@example.com", "M10 Match Host")
    _onboard(client, host_h, "M10 Match Host Co")

    created = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"invite_identifier": "m10-match-invitee@example.com", "role": "viewer"},
    )
    assert created.status_code == 201
    token = _invite_token(db_session, "m10-match-invitee@example.com")

    wrong_h = _auth(client, "m10-match-wrong@example.com", "Wrong Match")
    bad = client.post(f"/api/v1/team/invites/{token}/accept", headers=wrong_h)
    assert bad.status_code == 403
    assert "invited email" in bad.json()["detail"].lower()

    right_h = _auth(client, "m10-match-invitee@example.com", "Right Match")
    ok = client.post(f"/api/v1/team/invites/{token}/accept", headers=right_h)
    assert ok.status_code == 200, ok.text


def test_self_invite_is_blocked(client: TestClient, db_session: Session):
    host_h = _auth(client, "m10-self-host@example.com", "M10 Self Host")
    _onboard(client, host_h, "M10 Self Host Co")
    host_user = db_session.scalar(
        select(User).where(User.email == "m10-self-host@example.com")
    )
    assert host_user is not None
    _set_username(db_session, host_user, "m10_self_host")

    by_email = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"invite_identifier": "m10-self-host@example.com", "role": "admin"},
    )
    assert by_email.status_code == 400
    assert "yourself" in by_email.json()["detail"].lower() or "owner" in by_email.json()[
        "detail"
    ].lower()

    by_username = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"invite_identifier": "@m10_self_host", "role": "admin"},
    )
    assert by_username.status_code == 400


def test_existing_active_team_member_invite_is_blocked(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "m10-active-host@example.com", "M10 Active Host")
    _onboard(client, host_h, "M10 Active Host Co")
    member_h = _auth(client, "m10-active-member@example.com", "Active Member")
    member = db_session.scalar(
        select(User).where(User.email == "m10-active-member@example.com")
    )
    assert member is not None
    _set_username(db_session, member, "m10_active")

    invited = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"invite_identifier": "m10-active-member@example.com", "role": "scanner"},
    )
    assert invited.status_code == 201
    token = _invite_token(db_session, "m10-active-member@example.com")
    accepted = client.post(
        f"/api/v1/team/invites/{token}/accept",
        headers=member_h,
    )
    assert accepted.status_code == 200

    again_email = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"invite_identifier": "m10-active-member@example.com", "role": "viewer"},
    )
    assert again_email.status_code == 409
    assert "already" in again_email.json()["detail"].lower()

    again_username = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"invite_identifier": "@m10_active", "role": "viewer"},
    )
    assert again_username.status_code == 409


def test_invite_email_event_is_created(client: TestClient, db_session: Session):
    host_h = _auth(client, "m10-mail-host@example.com", "M10 Mail Host")
    _onboard(client, host_h, "M10 Mail Host Co")

    created = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"invite_identifier": "m10-mail-invitee@example.com", "role": "viewer"},
    )
    assert created.status_code == 201
    email_row = db_session.scalar(
        select(EmailEvent)
        .where(
            EmailEvent.template == "team_invite",
            EmailEvent.recipient_email == "m10-mail-invitee@example.com",
        )
        .order_by(EmailEvent.created_at.desc())
    )
    assert email_row is not None
    assert (email_row.context_json or {}).get("invite_path")


def test_in_app_notification_created_if_supported(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "m10-notif-host@example.com", "M10 Notif Host")
    _onboard(client, host_h, "M10 Notif Host Co")
    _auth(client, "m10-notif-member@example.com", "Notif Member")
    member = db_session.scalar(
        select(User).where(User.email == "m10-notif-member@example.com")
    )
    assert member is not None
    _set_username(db_session, member, "m10_notif")

    created = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"invite_identifier": "@m10_notif", "role": "viewer"},
    )
    assert created.status_code == 201
    note = db_session.scalar(
        select(InAppNotification).where(
            InAppNotification.user_id == member.id,
            InAppNotification.kind == "team.invite",
        )
    )
    assert note is not None
    assert "@m10_notif" in (note.body or "")


def test_audit_log_records_invite_method(client: TestClient, db_session: Session):
    host_h = _auth(client, "m10-audit-host@example.com", "M10 Audit Host")
    host = _onboard(client, host_h, "M10 Audit Host Co")
    host_id = UUID(host["id"])
    _auth(client, "m10-audit-member@example.com", "Audit Member")
    member = db_session.scalar(
        select(User).where(User.email == "m10-audit-member@example.com")
    )
    assert member is not None
    _set_username(db_session, member, "m10_audit")

    email_invite = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"invite_identifier": "m10-audit-email@example.com", "role": "viewer"},
    )
    assert email_invite.status_code == 201
    email_invite_id = email_invite.json()["invite_id"]

    uname_invite = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"invite_identifier": "@m10_audit", "role": "scanner"},
    )
    assert uname_invite.status_code == 201
    uname_invite_id = uname_invite.json()["invite_id"]

    email_log = db_session.scalar(
        select(HostTeamAuditLog).where(
            HostTeamAuditLog.host_id == host_id,
            HostTeamAuditLog.action == "hosts.team_invite",
            HostTeamAuditLog.entity_id == email_invite_id,
        )
    )
    assert email_log is not None
    email_meta = email_log.metadata_json or {}
    assert email_meta.get("invite_method") == "email"
    assert email_meta.get("invited_email") == "m10-audit-email@example.com"
    assert "invited_username" not in email_meta

    uname_log = db_session.scalar(
        select(HostTeamAuditLog).where(
            HostTeamAuditLog.host_id == host_id,
            HostTeamAuditLog.action == "hosts.team_invite",
            HostTeamAuditLog.entity_id == uname_invite_id,
        )
    )
    assert uname_log is not None
    uname_meta = uname_log.metadata_json or {}
    assert uname_meta.get("invite_method") == "username"
    assert uname_meta.get("invited_username") in {"m10_audit", "@m10_audit"}
    assert "invited_email" not in uname_meta
    assert "m10-audit-member@example.com" not in str(uname_meta)
