"""Edit, reply, pin, star — permissions and privacy for chat features."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.crm.models import HostFollower
from app.hosts.models import Host, HostProfile
from app.users.models import User
from app.users.service import get_role_by_name


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


def _seed_host(db: Session, email: str = "cf-host@example.com") -> Host:
    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="CF Host",
        is_active=True,
    )
    user.roles.append(get_role_by_name(db, "host"))
    db.add(user)
    db.flush()
    host = Host(
        user_id=user.id,
        display_name="CF Host",
        slug="cf-host-" + uuid4().hex[:6],
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="Host", city="Lagos"))
    db.commit()
    return host


def _open_thread(client: TestClient, db: Session, fan_h: dict, host: Host) -> str:
    fan = db.query(User).filter(User.email == "cf-fan@example.com").one()
    db.add(HostFollower(host_id=host.id, user_id=fan.id))
    db.commit()
    r = client.post(
        "/api/v1/messages/threads",
        headers=fan_h,
        json={"host_id": str(host.id), "body": "Hello chat features"},
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_edit_own_message_sets_edited_at(client: TestClient, db_session: Session):
    from uuid import UUID

    from app.messaging.models import Message, MessageEdit

    host = _seed_host(db_session)
    fan_h = _auth(client, "cf-fan@example.com", "CF Fan")
    tid = _open_thread(client, db_session, fan_h, host)
    detail = client.get(f"/api/v1/messages/{tid}", headers=fan_h).json()
    mid = detail["messages"][-1]["id"]

    edited = client.patch(
        f"/api/v1/messages/{mid}",
        headers=fan_h,
        json={"body": "Edited hello"},
    )
    assert edited.status_code == 200, edited.text
    body = edited.json()
    assert body["body"] == "Edited hello"
    assert body["edited_at"] is not None

    row = db_session.get(Message, UUID(mid))
    assert row is not None
    assert row.edit_count == 1
    assert row.last_edited_by_user_id is not None
    hist = (
        db_session.query(MessageEdit)
        .filter(MessageEdit.message_id == row.id)
        .all()
    )
    assert len(hist) == 1
    assert hist[0].previous_body == "Hello chat features"
    assert hist[0].new_body == "Edited hello"

    # Latest-message edit updates inbox preview.
    listed = client.get("/api/v1/messages", headers=fan_h).json()
    item = next(t for t in listed["items"] if t["id"] == tid)
    assert "Edited hello" in (item["last_message_preview"] or "")


def test_edit_peer_message_forbidden(client: TestClient, db_session: Session):
    host = _seed_host(db_session)
    fan_h = _auth(client, "cf-fan@example.com", "CF Fan")
    tid = _open_thread(client, db_session, fan_h, host)
    mid = client.get(f"/api/v1/messages/{tid}", headers=fan_h).json()["messages"][-1][
        "id"
    ]
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "cf-host@example.com", "password": "securepass1"},
    )
    host_h = {"Authorization": f"Bearer {login.json()['access_token']}"}
    r = client.patch(
        f"/api/v1/host/messages/{mid}",
        headers=host_h,
        json={"body": "Nope"},
    )
    assert r.status_code == 403


def test_edit_empty_body_rejected(client: TestClient, db_session: Session):
    host = _seed_host(db_session)
    fan_h = _auth(client, "cf-fan@example.com", "CF Fan")
    _open_thread(client, db_session, fan_h, host)
    tid = client.get("/api/v1/messages", headers=fan_h).json()["items"][0]["id"]
    mid = client.get(f"/api/v1/messages/{tid}", headers=fan_h).json()["messages"][-1][
        "id"
    ]
    r = client.patch(
        f"/api/v1/messages/{mid}",
        headers=fan_h,
        json={"body": "   "},
    )
    assert r.status_code == 422


def test_edit_outside_window_rejected(client: TestClient, db_session: Session):
    from datetime import UTC, datetime, timedelta
    from uuid import UUID

    from app.messaging.models import Message

    host = _seed_host(db_session)
    fan_h = _auth(client, "cf-fan@example.com", "CF Fan")
    tid = _open_thread(client, db_session, fan_h, host)
    mid = client.get(f"/api/v1/messages/{tid}", headers=fan_h).json()["messages"][-1][
        "id"
    ]
    row = db_session.get(Message, UUID(mid))
    assert row is not None
    row.created_at = datetime.now(UTC) - timedelta(hours=25)
    db_session.commit()
    r = client.patch(
        f"/api/v1/messages/{mid}",
        headers=fan_h,
        json={"body": "Too late"},
    )
    assert r.status_code == 400
    assert "24" in r.json()["detail"]


def test_reply_to_same_thread(client: TestClient, db_session: Session):
    host = _seed_host(db_session)
    fan_h = _auth(client, "cf-fan@example.com", "CF Fan")
    tid = _open_thread(client, db_session, fan_h, host)
    parent = client.get(f"/api/v1/messages/{tid}", headers=fan_h).json()["messages"][-1][
        "id"
    ]
    r = client.post(
        f"/api/v1/messages/{tid}/send",
        headers=fan_h,
        json={"body": "Replying", "reply_to_message_id": parent},
    )
    assert r.status_code == 200, r.text
    reply = r.json()["reply_to"]
    assert reply["reply_message_id"] == parent
    assert reply["reply_is_unavailable"] is False
    assert "Hello" in (reply["reply_body_preview"] or "")
    assert reply["reply_author_display_name"]
    assert reply["reply_created_at"]


def test_reply_preview_unavailable_when_parent_hidden(
    client: TestClient, db_session: Session
):
    from uuid import UUID

    from app.messaging import constants as C
    from app.messaging.models import Message

    host = _seed_host(db_session)
    fan_h = _auth(client, "cf-fan@example.com", "CF Fan")
    tid = _open_thread(client, db_session, fan_h, host)
    parent = client.get(f"/api/v1/messages/{tid}", headers=fan_h).json()["messages"][-1][
        "id"
    ]
    sent = client.post(
        f"/api/v1/messages/{tid}/send",
        headers=fan_h,
        json={"body": "Replying", "reply_to_message_id": parent},
    )
    assert sent.status_code == 200
    child_id = sent.json()["id"]

    row = db_session.get(Message, UUID(parent))
    assert row is not None
    row.status = C.MESSAGE_STATUS_HIDDEN
    row.moderation_status = C.MOD_HIDDEN
    db_session.commit()

    detail = client.get(f"/api/v1/messages/{tid}", headers=fan_h).json()
    child = next(m for m in detail["messages"] if m["id"] == child_id)
    assert child["reply_to"]["reply_is_unavailable"] is True
    assert child["reply_to"]["reply_body_preview"] == "Message unavailable"


def test_reply_cross_thread_rejected(client: TestClient, db_session: Session):
    host = _seed_host(db_session)
    fan_h = _auth(client, "cf-fan@example.com", "CF Fan")
    tid = _open_thread(client, db_session, fan_h, host)
    fake_id = str(uuid4())
    r = client.post(
        f"/api/v1/messages/{tid}/send",
        headers=fan_h,
        json={"body": "Bad reply", "reply_to_message_id": fake_id},
    )
    assert r.status_code == 404


def test_pin_max_three_and_shared(client: TestClient, db_session: Session):
    host = _seed_host(db_session)
    fan_h = _auth(client, "cf-fan@example.com", "CF Fan")
    tid = _open_thread(client, db_session, fan_h, host)
    ids = []
    for i in range(4):
        r = client.post(
            f"/api/v1/messages/{tid}/send",
            headers=fan_h,
            json={"body": f"Pin candidate {i}"},
        )
        assert r.status_code == 200
        ids.append(r.json()["id"])

    for mid in ids[:3]:
        r = client.post(f"/api/v1/messages/{mid}/pin", headers=fan_h)
        assert r.status_code == 200, r.text
        assert r.json()["total"] <= 3

    r = client.post(f"/api/v1/messages/{ids[3]}/pin", headers=fan_h)
    assert r.status_code == 400

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "cf-host@example.com", "password": "securepass1"},
    )
    host_h = {"Authorization": f"Bearer {login.json()['access_token']}"}
    pins = client.get(
        f"/api/v1/host/messages/threads/{tid}/pins", headers=host_h
    ).json()
    assert pins["total"] == 3


def test_unpin(client: TestClient, db_session: Session):
    from uuid import UUID

    from app.messaging.models import MessagePin

    host = _seed_host(db_session)
    fan_h = _auth(client, "cf-fan@example.com", "CF Fan")
    tid = _open_thread(client, db_session, fan_h, host)
    mid = client.get(f"/api/v1/messages/{tid}", headers=fan_h).json()["messages"][-1][
        "id"
    ]
    client.post(f"/api/v1/messages/{mid}/pin", headers=fan_h)
    r = client.post(f"/api/v1/messages/{mid}/unpin", headers=fan_h)
    assert r.status_code == 200
    assert r.json()["items"] == []
    row = (
        db_session.query(MessagePin)
        .filter(MessagePin.message_id == UUID(mid))
        .one()
    )
    assert row.unpinned_at is not None


def test_star_personal_isolation(client: TestClient, db_session: Session):
    host = _seed_host(db_session)
    fan_h = _auth(client, "cf-fan@example.com", "CF Fan")
    tid = _open_thread(client, db_session, fan_h, host)
    mid = client.get(f"/api/v1/messages/{tid}", headers=fan_h).json()["messages"][-1][
        "id"
    ]
    r = client.post(f"/api/v1/messages/{mid}/star", headers=fan_h)
    assert r.status_code == 200
    assert r.json()["is_starred"] is True

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "cf-host@example.com", "password": "securepass1"},
    )
    host_h = {"Authorization": f"Bearer {login.json()['access_token']}"}
    host_view = client.get(f"/api/v1/host/messages/{tid}", headers=host_h).json()
    host_msg = next(m for m in host_view["messages"] if m["id"] == mid)
    assert host_msg["is_starred"] is False

    starred = client.get("/api/v1/messages/starred", headers=fan_h).json()
    assert starred["total"] >= 1
    assert any(i["message"]["id"] == mid for i in starred["items"])

    un = client.post(f"/api/v1/messages/{mid}/unstar", headers=fan_h)
    assert un.status_code == 200
    assert un.json()["is_starred"] is False
    from uuid import UUID

    from app.messaging.models import MessageStar

    row = (
        db_session.query(MessageStar)
        .filter(MessageStar.message_id == UUID(mid))
        .one()
    )
    assert row.unstarred_at is not None
    assert client.get("/api/v1/messages/starred", headers=fan_h).json()["total"] == 0

    # Soft re-star
    again = client.post(f"/api/v1/messages/{mid}/star", headers=fan_h)
    assert again.status_code == 200
    assert again.json()["is_starred"] is True
    db_session.refresh(row)
    assert row.unstarred_at is None


def test_serialize_includes_chat_metadata(client: TestClient, db_session: Session):
    host = _seed_host(db_session)
    fan_h = _auth(client, "cf-fan@example.com", "CF Fan")
    tid = _open_thread(client, db_session, fan_h, host)
    parent = client.get(f"/api/v1/messages/{tid}", headers=fan_h).json()["messages"][-1][
        "id"
    ]
    client.post(
        f"/api/v1/messages/{tid}/send",
        headers=fan_h,
        json={"body": "With meta", "reply_to_message_id": parent},
    )
    mid = client.get(f"/api/v1/messages/{tid}", headers=fan_h).json()["messages"][-1][
        "id"
    ]
    client.post(f"/api/v1/messages/{mid}/pin", headers=fan_h)
    client.post(f"/api/v1/messages/{mid}/star", headers=fan_h)
    client.patch(
        f"/api/v1/messages/{mid}",
        headers=fan_h,
        json={"body": "Edited meta"},
    )
    msg = client.get(f"/api/v1/messages/{tid}", headers=fan_h).json()["messages"][-1]
    assert msg["edited_at"]
    assert msg["reply_to"]["reply_message_id"] == parent
    assert msg["is_pinned"] is True
    assert msg["is_starred"] is True


def _admin_headers(
    client: TestClient, assign_role, email: str = "cf-admin@example.com"
) -> dict[str, str]:
    _auth(client, email, "CF Admin")
    assign_role(email, "super_admin")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _report_thread(client: TestClient, headers: dict[str, str], tid: str) -> None:
    r = client.post(
        f"/api/v1/messages/{tid}/report",
        headers=headers,
        json={"reason": "spam", "details": "privacy test"},
    )
    assert r.status_code == 201, r.text


def test_hide_clears_pin(
    client: TestClient, db_session: Session, assign_role
):
    host = _seed_host(db_session)
    fan_h = _auth(client, "cf-fan@example.com", "CF Fan")
    tid = _open_thread(client, db_session, fan_h, host)
    mid = client.get(f"/api/v1/messages/{tid}", headers=fan_h).json()["messages"][-1][
        "id"
    ]
    client.post(f"/api/v1/messages/{mid}/pin", headers=fan_h)
    _report_thread(client, fan_h, tid)

    admin_h = _admin_headers(client, assign_role)
    r = client.patch(f"/api/v1/admin/messages/{mid}/hide", headers=admin_h)
    assert r.status_code == 200, r.text
    detail = client.get(f"/api/v1/messages/{tid}", headers=fan_h).json()
    assert detail["pinned_messages"] == []


def test_starred_list_redacts_hidden(
    client: TestClient, db_session: Session, assign_role
):
    host = _seed_host(db_session)
    fan_h = _auth(client, "cf-fan@example.com", "CF Fan")
    tid = _open_thread(client, db_session, fan_h, host)
    send = client.post(
        f"/api/v1/messages/{tid}/send",
        headers=fan_h,
        json={"body": "Secret pickup code ALPHA"},
    )
    assert send.status_code == 200, send.text
    mid = send.json()["id"]
    assert client.post(f"/api/v1/messages/{mid}/star", headers=fan_h).status_code == 200
    _report_thread(client, fan_h, tid)

    admin_h = _admin_headers(client, assign_role)
    assert (
        client.patch(f"/api/v1/admin/messages/{mid}/hide", headers=admin_h).status_code
        == 200
    )
    starred = client.get("/api/v1/messages/starred", headers=fan_h).json()
    row = next(i for i in starred["items"] if i["message"]["id"] == mid)
    assert "ALPHA" not in (row["message"]["body"] or "")
    assert row["message"]["status"] == "hidden"


def test_delete_for_me_hides_for_viewer_only(
    client: TestClient, db_session: Session
):
    host = _seed_host(db_session)
    fan_h = _auth(client, "cf-fan@example.com", "CF Fan")
    tid = _open_thread(client, db_session, fan_h, host)
    mid = client.post(
        f"/api/v1/messages/{tid}/send",
        headers=fan_h,
        json={"body": "Secret pickup ALPHA-99"},
    ).json()["id"]
    client.post(f"/api/v1/messages/{mid}/star", headers=fan_h)
    client.post(f"/api/v1/messages/{mid}/pin", headers=fan_h)

    r = client.post(
        f"/api/v1/messages/{mid}/delete",
        headers=fan_h,
        json={"scope": "for_me"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["deleted_for_me"] is True
    assert r.json()["body"] == "Message deleted"
    assert "ALPHA" not in r.json()["body"]

    fan_detail = client.get(f"/api/v1/messages/{tid}", headers=fan_h).json()
    fan_msg = next(m for m in fan_detail["messages"] if m["id"] == mid)
    assert fan_msg["deleted_for_me"] is True
    assert fan_msg["body"] == "Message deleted"
    assert mid not in [m["id"] for m in fan_detail.get("pinned_messages") or []]

    starred = client.get("/api/v1/messages/starred", headers=fan_h).json()
    assert not any(i["message"]["id"] == mid for i in starred["items"])

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "cf-host@example.com", "password": "securepass1"},
    )
    host_h = {"Authorization": f"Bearer {login.json()['access_token']}"}
    host_detail = client.get(f"/api/v1/host/messages/{tid}", headers=host_h).json()
    host_msg = next(m for m in host_detail["messages"] if m["id"] == mid)
    assert host_msg.get("deleted_for_me") is False
    assert "ALPHA-99" in host_msg["body"]

    everyone = client.post(
        f"/api/v1/messages/{mid}/delete",
        headers=fan_h,
        json={"scope": "for_everyone"},
    )
    assert everyone.status_code == 400


def test_thread_search_body_and_starred_filter(
    client: TestClient, db_session: Session
):
    host = _seed_host(db_session)
    fan_h = _auth(client, "cf-fan@example.com", "CF Fan")
    tid = _open_thread(client, db_session, fan_h, host)
    a = client.post(
        f"/api/v1/messages/{tid}/send",
        headers=fan_h,
        json={"body": "Pickup at Gate B noon"},
    ).json()["id"]
    b = client.post(
        f"/api/v1/messages/{tid}/send",
        headers=fan_h,
        json={"body": "See you at the merch table"},
    ).json()["id"]
    assert client.post(f"/api/v1/messages/{a}/star", headers=fan_h).status_code == 200

    by_text = client.get(
        f"/api/v1/messages/threads/{tid}/search",
        headers=fan_h,
        params={"q": "Gate B"},
    )
    assert by_text.status_code == 200, by_text.text
    ids = [i["id"] for i in by_text.json()["items"]]
    assert a in ids
    assert b not in ids

    starred_only = client.get(
        f"/api/v1/messages/threads/{tid}/search",
        headers=fan_h,
        params={"starred": True},
    )
    assert starred_only.status_code == 200
    star_ids = [i["id"] for i in starred_only.json()["items"]]
    assert a in star_ids
    assert b not in star_ids

    empty = client.get(
        f"/api/v1/messages/threads/{tid}/search",
        headers=fan_h,
    )
    assert empty.status_code == 200
    assert empty.json()["items"] == []


def test_search_excludes_hidden_message_bodies(
    client: TestClient, db_session: Session
):
    from uuid import UUID

    from app.messaging import constants as C
    from app.messaging.models import Message

    host = _seed_host(db_session)
    fan_h = _auth(client, "cf-fan@example.com", "CF Fan")
    tid = _open_thread(client, db_session, fan_h, host)
    mid = client.post(
        f"/api/v1/messages/{tid}/send",
        headers=fan_h,
        json={"body": "HiddenPhraseZebra99"},
    ).json()["id"]
    row = db_session.get(Message, UUID(mid))
    assert row is not None
    row.status = C.MESSAGE_STATUS_HIDDEN
    row.moderation_status = C.MOD_HIDDEN
    db_session.commit()

    hit = client.get(
        f"/api/v1/messages/threads/{tid}/search",
        headers=fan_h,
        params={"q": "HiddenPhraseZebra99"},
    )
    assert hit.status_code == 200
    assert hit.json()["items"] == []


def test_inbox_preview_redacts_hidden_last_message(
    client: TestClient, db_session: Session, assign_role
):
    host = _seed_host(db_session)
    fan_h = _auth(client, "cf-fan@example.com", "CF Fan")
    tid = _open_thread(client, db_session, fan_h, host)
    mid = client.post(
        f"/api/v1/messages/{tid}/send",
        headers=fan_h,
        json={"body": "SecretPreviewBodyXYZ"},
    ).json()["id"]
    _report_thread(client, fan_h, tid)
    admin_h = _admin_headers(client, assign_role)
    assert (
        client.patch(f"/api/v1/admin/messages/{mid}/hide", headers=admin_h).status_code
        == 200
    )

    listed = client.get("/api/v1/messages", headers=fan_h).json()
    item = next(t for t in listed["items"] if t["id"] == tid)
    assert "SecretPreviewBodyXYZ" not in (item["last_message_preview"] or "")
    assert "hidden by moderation" in (item["last_message_preview"] or "").lower()


def test_reported_thread_disables_send(
    client: TestClient, db_session: Session
):
    host = _seed_host(db_session)
    fan_h = _auth(client, "cf-fan@example.com", "CF Fan")
    tid = _open_thread(client, db_session, fan_h, host)
    _report_thread(client, fan_h, tid)

    detail = client.get(f"/api/v1/messages/{tid}", headers=fan_h).json()
    assert detail["can_reply"] is False

    denied = client.post(
        f"/api/v1/messages/{tid}/send",
        headers=fan_h,
        json={"body": "Should not send"},
    )
    assert denied.status_code == 403


def test_admin_hide_requires_report(
    client: TestClient, db_session: Session, assign_role
):
    host = _seed_host(db_session)
    fan_h = _auth(client, "cf-fan@example.com", "CF Fan")
    tid = _open_thread(client, db_session, fan_h, host)
    mid = client.get(f"/api/v1/messages/{tid}", headers=fan_h).json()["messages"][-1][
        "id"
    ]
    admin_h = _admin_headers(client, assign_role)
    r = client.patch(f"/api/v1/admin/messages/{mid}/hide", headers=admin_h)
    assert r.status_code == 403
    assert "reported" in r.json()["detail"].lower()
