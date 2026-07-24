"""Team email templates + lifecycle notifications."""

from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.email.models import EmailEvent
from app.email.templates import get_template, render_subject
from app.messaging.models import InAppNotification


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
            "bio": "Notify host",
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


def test_team_invite_template_copy():
    tpl = get_template("team_invite")
    subject = render_subject(tpl, {})
    assert subject == "You're invited to join a Pàdéyá host team"
    assert tpl.cta_label == "Accept invite"

    email_body = tpl.body_fn(
        {"host_display_name": "Lagos Nights", "invite_method": "email"}
    )
    assert "You’ve been invited to join Lagos Nights’s Pàdéyá team." in email_body

    username_body = tpl.body_fn(
        {
            "host_display_name": "Lagos Nights",
            "invite_method": "username",
            "invited_username": "gatekeeper",
        }
    )
    assert (
        "Lagos Nights invited your Pàdéyá account @gatekeeper to join their team."
        in username_body
    )


def test_username_invite_email_and_in_app_copy(
    client: TestClient, db_session: Session
):
    from app.passport.privacy import VISIBILITY_PUBLIC
    from app.passport.service import ensure_passport
    from app.users.models import User

    host_h = _auth(client, "tpl-uname-host@example.com", "Tpl Uname Host")
    _onboard(client, host_h, "Tpl Host Co")
    member_h = _auth(client, "tpl-uname-member@example.com", "Tpl Member")
    member = db_session.scalar(
        select(User).where(User.email == "tpl-uname-member@example.com")
    )
    assert member is not None
    passport = ensure_passport(db_session, member)
    passport.username = "tpl_gate"
    passport.visibility = VISIBILITY_PUBLIC
    db_session.commit()

    created = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"invite_identifier": "@tpl_gate", "role": "viewer"},
    )
    assert created.status_code == 201, created.text

    invite_mail = db_session.scalar(
        select(EmailEvent)
        .where(
            EmailEvent.template == "team_invite",
            EmailEvent.recipient_email == "tpl-uname-member@example.com",
        )
        .order_by(EmailEvent.created_at.desc())
    )
    assert invite_mail is not None
    ctx = invite_mail.context_json or {}
    assert ctx.get("invite_method") == "username"
    assert ctx.get("invited_username") == "tpl_gate"
    rendered = get_template("team_invite").body_fn(ctx)
    assert (
        "Tpl Host Co invited your Pàdéyá account @tpl_gate to join their team."
        in rendered
    )

    note = db_session.scalar(
        select(InAppNotification).where(
            InAppNotification.user_id == member.id,
            InAppNotification.kind == "team.invite",
        )
    )
    assert note is not None
    assert (
        note.body
        == "Tpl Host Co invited your Pàdéyá account @tpl_gate to join their team."
    )

    # Accept → host gets in-app (+ email)
    token = (ctx.get("invite_path") or "").rsplit("/", 1)[-1]
    accepted = client.post(
        f"/api/v1/team/invites/{token}/accept",
        headers=member_h,
    )
    assert accepted.status_code == 200, accepted.text
    host_note = db_session.scalar(
        select(InAppNotification).where(
            InAppNotification.kind == "team.invite_accepted"
        )
    )
    assert host_note is not None
    assert (
        db_session.scalar(
            select(EmailEvent).where(EmailEvent.template == "team_invite_accepted")
        )
        is not None
    )


def test_email_invite_known_user_gets_in_app(
    client: TestClient, db_session: Session
):
    from app.users.models import User

    host_h = _auth(client, "tpl-email-host@example.com", "Tpl Email Host")
    _onboard(client, host_h, "Email Host Co")
    _auth(client, "tpl-email-member@example.com", "Known Member")
    member = db_session.scalar(
        select(User).where(User.email == "tpl-email-member@example.com")
    )
    assert member is not None

    created = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"invite_identifier": "tpl-email-member@example.com", "role": "scanner"},
    )
    assert created.status_code == 201, created.text

    invite_mail = db_session.scalar(
        select(EmailEvent)
        .where(
            EmailEvent.template == "team_invite",
            EmailEvent.recipient_email == "tpl-email-member@example.com",
        )
        .order_by(EmailEvent.created_at.desc())
    )
    assert invite_mail is not None
    ctx = invite_mail.context_json or {}
    assert (ctx.get("invite_method") or "email") == "email"
    rendered = get_template("team_invite").body_fn(ctx)
    assert "You’ve been invited to join Email Host Co’s Pàdéyá team." in rendered

    note = db_session.scalar(
        select(InAppNotification).where(
            InAppNotification.user_id == member.id,
            InAppNotification.kind == "team.invite",
        )
    )
    assert note is not None
    assert note.body == "You’ve been invited to join Email Host Co’s Pàdéyá team."


def test_invite_accept_revoke_remove_permission_emails(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "notify-host@example.com", "Notify Host")
    host = _onboard(client, host_h, "Notify Host Co")

    created = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"email": "notify-member@example.com", "role": "scanner"},
    )
    assert created.status_code == 201, created.text
    invite_id = created.json()["invite_id"]

    invite_mail = db_session.scalar(
        select(EmailEvent)
        .where(
            EmailEvent.template == "team_invite",
            EmailEvent.recipient_email == "notify-member@example.com",
        )
        .order_by(EmailEvent.created_at.desc())
    )
    assert invite_mail is not None
    assert "invited to join a Pàdéyá host team" in invite_mail.subject

    token = _invite_token(db_session, "notify-member@example.com")
    member_h = _auth(client, "notify-member@example.com", "Notify Member")
    accepted = client.post(
        f"/api/v1/team/invites/{token}/accept",
        headers=member_h,
    )
    assert accepted.status_code == 200, accepted.text
    member_id = accepted.json()["id"]

    accepted_mail = db_session.scalar(
        select(EmailEvent).where(EmailEvent.template == "team_invite_accepted")
    )
    assert accepted_mail is not None
    assert accepted_mail.recipient_email == "notify-host@example.com"

    host_note = db_session.scalar(
        select(InAppNotification).where(
            InAppNotification.kind == "team.invite_accepted"
        )
    )
    assert host_note is not None

    # Fresh invite to revoke
    created2 = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"email": "notify-revoke@example.com", "role": "viewer"},
    )
    assert created2.status_code == 201
    revoke_id = created2.json()["invite_id"]
    revoked = client.post(
        f"/api/v1/host/team/invites/{revoke_id}/revoke",
        headers=host_h,
    )
    assert revoked.status_code == 200
    assert (
        db_session.scalar(
            select(EmailEvent).where(EmailEvent.template == "team_invite_revoked")
        )
        is not None
    )

    # Permission update + suspend + remove on accepted member
    patched = client.patch(
        f"/api/v1/host/team/members/{member_id}?host_id={host['id']}",
        headers=host_h,
        json={"role": "merch_staff", "role_label": "Merch Staff"},
    )
    assert patched.status_code == 200, patched.text
    assert (
        db_session.scalar(
            select(EmailEvent).where(EmailEvent.template == "team_permission_updated")
        )
        is not None
    )
    member_note = db_session.scalar(
        select(InAppNotification).where(
            InAppNotification.kind == "team.permission_updated"
        )
    )
    assert member_note is not None

    suspended = client.post(
        f"/api/v1/host/team/members/{member_id}/suspend?host_id={host['id']}",
        headers=host_h,
    )
    assert suspended.status_code == 200
    assert (
        db_session.scalar(
            select(EmailEvent).where(EmailEvent.template == "team_security_alert")
        )
        is not None
    )

    # Restore then remove for clean removed email
    client.post(
        f"/api/v1/hosts/{host['id']}/team/{member_id}/restore",
        headers=host_h,
    )
    removed = client.post(
        f"/api/v1/host/team/members/{member_id}/remove?host_id={host['id']}",
        headers=host_h,
    )
    assert removed.status_code == 200
    assert (
        db_session.scalar(
            select(EmailEvent).where(EmailEvent.template == "team_member_removed")
        )
        is not None
    )

    # Sanity: invite id ≠ member id after accept
    assert UUID(member_id) != UUID(invite_id)
