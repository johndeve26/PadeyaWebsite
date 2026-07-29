"""Vault access, unlock, and moderation tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.tickets.models import Ticket
from app.tickets.qr import new_public_ticket_code
from app.users.models import User
from app.users.service import get_role_by_name
from app.vault.service import finalize_vault_purchase, get_vault_purchase_by_reference


def _register(client: TestClient, email: str, name: str = "User") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name, "gender": "prefer_not_to_say"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed_host(
    db: Session,
    *,
    email: str = "vault-host@example.com",
    slug: str = "vault-host",
    display_name: str = "Vault Host",
) -> tuple[Host, User]:
    host_user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name=display_name,
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    host_user.roles.append(role)
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name=display_name,
        slug=slug,
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio=f"{display_name} bio"))
    db.commit()
    return host, host_user


def test_create_and_access_free_item(client: TestClient, db_session: Session):
    _, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)

    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Free drop",
            "content_type": "text_post",
            "preview_text": "A free preview",
            "body": "Full free body content here",
            "status": "published",
            "access": {"access_type": "free"},
            "media": [
                {
                    "url": "https://cdn.example.com/preview.jpg",
                    "media_type": "image",
                    "is_preview": True,
                },
                {
                    "url": "https://cdn.example.com/secret.mp4",
                    "media_type": "video",
                    "is_preview": False,
                },
            ],
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["has_access"] is True
    assert created.json()["body"] == "Full free body content here"

    public = client.get("/api/v1/vault/public/vault-host/free-drop")
    assert public.status_code == 200, public.text
    assert public.json()["locked"] is False
    assert public.json()["body"] == "Full free body content here"
    urls = [m["url"] for m in public.json()["media"]]
    assert "https://cdn.example.com/secret.mp4" in urls


def test_block_locked_item_without_access(client: TestClient, db_session: Session):
    _, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)

    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Followers exclusive",
            "content_type": "vip_content",
            "preview_text": "Teaser only",
            "body": "SECRET BODY",
            "status": "published",
            "access": {"access_type": "followers_only"},
            "media": [
                {
                    "url": "https://cdn.example.com/locked.mp4",
                    "media_type": "video",
                    "is_preview": False,
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    slug = created.json()["slug"]

    anon = client.get(f"/api/v1/vault/public/vault-host/{slug}")
    assert anon.status_code == 200
    assert anon.json()["locked"] is True
    assert anon.json()["body"] is None
    assert anon.json()["file_url"] is None
    assert anon.json()["external_url"] is None
    # Private media omitted entirely when locked (not returned with null URL)
    assert anon.json()["media"] == []
    assert anon.json()["access"]["access_code"] is None

    buyer = _register(client, "vault-fan@example.com")
    blocked = client.get(f"/api/v1/vault/public/vault-host/{slug}", headers=buyer)
    assert blocked.json()["locked"] is True
    assert blocked.json()["access_reason"] == "followers_only"


def test_one_time_unlock_purchase(client: TestClient, db_session: Session):
    _, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)
    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Paid replay",
            "content_type": "ticket_holder_recap",
            "preview_text": "Buy to unlock",
            "body": "REPLAY CONTENT",
            "price": "2500.00",
            "status": "published",
            "access": {"access_type": "one_time_unlock"},
            "media": [
                {
                    "url": "https://cdn.example.com/replay.mp4",
                    "media_type": "video",
                    "is_preview": False,
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]
    slug = created.json()["slug"]

    buyer = _register(client, "vault-buyer@example.com")
    locked = client.get(f"/api/v1/vault/public/vault-host/{slug}", headers=buyer)
    assert locked.json()["locked"] is True

    with patch(
        "app.vault.service.initialize_transaction",
        return_value={
            "authorization_url": "https://paystack.test/auth",
            "access_code": "ACCESS",
        },
    ):
        checkout = client.post(f"/api/v1/vault/unlock/{item_id}", headers=buyer)
    assert checkout.status_code == 201, checkout.text
    assert checkout.json()["purchase"]["status"] == "pending"
    reference = checkout.json()["purchase"]["payment_reference"]

    purchase = get_vault_purchase_by_reference(db_session, reference)
    assert purchase is not None
    finalize_vault_purchase(
        db_session,
        purchase=purchase,
        provider_payment_id="pay_1",
        raw_payload={"ok": True},
        actor_user_id=purchase.user_id,
    )
    db_session.commit()

    unlocked = client.get(f"/api/v1/vault/public/vault-host/{slug}", headers=buyer)
    assert unlocked.status_code == 200
    assert unlocked.json()["locked"] is False
    assert unlocked.json()["body"] == "REPLAY CONTENT"
    assert unlocked.json()["media"][0]["url"] == "https://cdn.example.com/replay.mp4"

    earnings = client.get("/api/v1/vault/host/earnings", headers=host_headers)
    assert earnings.status_code == 200
    assert Decimal(earnings.json()["gross_revenue"]) == Decimal("2500.00")


def test_ticket_holder_access_and_block(client: TestClient, db_session: Session):
    host, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)

    buyer = User(
        email="ticket-fan@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Ticket Fan",
        is_active=True,
    )
    buyer.roles.append(get_role_by_name(db_session, "buyer"))
    db_session.add(buyer)
    db_session.flush()

    stranger = User(
        email="no-ticket@example.com",
        password_hash=hash_password("securepass1"),
        full_name="No Ticket",
        is_active=True,
    )
    stranger.roles.append(get_role_by_name(db_session, "buyer"))
    db_session.add(stranger)
    db_session.flush()

    category = db_session.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=5)
    event = Event(
        title="Vault Night",
        slug="vault-night",
        description="Event for vault ticket holder access tests with detail.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        city="Lagos",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
    )
    db_session.add(event)
    db_session.flush()
    tt = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
        price=Decimal("3000.00"),
        quantity=50,
        quantity_sold=1,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=4,
        visibility="public",
        status="active",
    )
    db_session.add(tt)
    db_session.flush()
    from app.payments.models import Order, OrderItem

    order = Order(
        reference="PDY-VAULT-TIX",
        buyer_user_id=buyer.id,
        event_id=event.id,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("3000.00"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("3000.00"),
        buyer_email=buyer.email,
        buyer_name=buyer.full_name,
        paid_at=datetime.now(UTC),
    )
    db_session.add(order)
    db_session.flush()
    item = OrderItem(
        order_id=order.id,
        ticket_type_id=tt.id,
        quantity=1,
        unit_price=Decimal("3000.00"),
        line_total=Decimal("3000.00"),
        ticket_type_name=tt.name,
    )
    db_session.add(item)
    db_session.flush()
    db_session.add(
        Ticket(
            public_code=new_public_ticket_code(),
            order_id=order.id,
            order_item_id=item.id,
            event_id=event.id,
            ticket_type_id=tt.id,
            buyer_user_id=buyer.id,
            status="active",
            ticket_type_name=tt.name,
            holder_name=buyer.full_name,
            holder_email=buyer.email,
        )
    )
    db_session.commit()

    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Ticket holders only",
            "content_type": "early_access",
            "preview_text": "For ticket holders",
            "body": "BACKSTAGE NOTES",
            "status": "published",
            "access": {"access_type": "ticket_holder_only"},
            "media": [],
        },
    )
    assert created.status_code == 201, created.text
    slug = created.json()["slug"]

    buyer_headers = _login(client, "ticket-fan@example.com")
    ok = client.get(f"/api/v1/vault/public/vault-host/{slug}", headers=buyer_headers)
    assert ok.status_code == 200
    assert ok.json()["locked"] is False
    assert ok.json()["body"] == "BACKSTAGE NOTES"

    stranger_headers = _login(client, "no-ticket@example.com")
    blocked = client.get(
        f"/api/v1/vault/public/vault-host/{slug}", headers=stranger_headers
    )
    assert blocked.json()["locked"] is True
    assert blocked.json()["access_reason"] == "ticket_required"
    assert blocked.json()["body"] is None


def test_admin_moderation(client: TestClient, db_session: Session, assign_role):
    _, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)
    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Flaggable item",
            "content_type": "image_gallery",
            "preview_text": "Preview",
            "body": "Body",
            "status": "published",
            "access": {"access_type": "free"},
            "media": [],
        },
    )
    item_id = created.json()["id"]
    slug = created.json()["slug"]

    _register(client, "vault-mod@example.com", "Mod")
    assign_role("vault-mod@example.com", "finance_admin")
    mod_headers = _login(client, "vault-mod@example.com")

    removed = client.post(
        f"/api/v1/vault/admin/items/{item_id}/moderate",
        headers=mod_headers,
        json={"action": "remove", "note": "Policy violation"},
    )
    assert removed.status_code == 200, removed.text
    assert removed.json()["moderation_status"] == "removed"
    assert removed.json()["status"] == "archived"
    assert removed.json()["moderation_status"] == "removed"

    gone = client.get(f"/api/v1/vault/public/vault-host/{slug}")
    assert gone.status_code == 404


def test_vault_studio_summary_and_fan_preview(client: TestClient, db_session: Session):
    host, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)

    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Studio locked drop",
            "content_type": "vip_content",
            "preview_text": "Public teaser",
            "body": "SECRET STUDIO BODY",
            "cover_url": "https://cdn.example.com/cover.jpg",
            "status": "published",
            "access": {"access_type": "followers_only"},
            "media": [
                {
                    "url": "https://cdn.example.com/teaser.jpg",
                    "media_type": "image",
                    "is_preview": True,
                },
                {
                    "url": "https://cdn.example.com/private.mp4",
                    "media_type": "video",
                    "is_preview": False,
                },
            ],
        },
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]

    studio = client.get("/api/v1/vault/host/studio", headers=host_headers)
    assert studio.status_code == 200, studio.text
    body = studio.json()
    assert body["host_username"] == host.slug
    assert body["share_path"] == f"/@{host.slug}/vault"
    assert len(body["items"]) >= 1
    assert "earnings" in body
    assert body["legacy_vault_block_visible"] is True
    assert "stats" in body
    assert body["stats"]["total_items"] >= 1
    assert body["stats"]["published_items"] >= 1
    assert body["stats"]["locked_items"] >= 1
    assert body["stats"]["free_items"] >= 0
    assert "paid_unlocks" in body["stats"]
    assert "view_count" in body["stats"]
    assert "gross_revenue" in body["stats"]
    studio_item = next(i for i in body["items"] if i["id"] == item_id)
    assert studio_item["is_access_gated"] is True
    assert studio_item["is_paid"] is False
    assert studio_item["is_ticket_gated"] is False
    assert studio_item["is_archived"] is False
    assert "view_count" in studio_item
    assert "unlock_count" in studio_item
    assert "earnings" in studio_item
    assert "top_item" in body

    fan_preview = client.get(
        f"/api/v1/vault/host/items/{item_id}/preview",
        headers=host_headers,
    )
    assert fan_preview.status_code == 200, fan_preview.text
    preview = fan_preview.json()
    assert preview["locked"] is True
    assert preview["body"] is None
    assert preview["file_url"] is None
    assert preview["external_url"] is None
    assert preview["preview_text"] == "Public teaser"
    assert preview["access"]["access_code"] is None
    # Only public preview media is returned for locked fan preview
    assert len(preview["media"]) == 1
    assert preview["media"][0]["is_preview"] is True
    assert preview["media"][0]["url"] is not None
    assert all(m.get("url") != "https://cdn.example.com/private.mp4" for m in preview["media"])

    owner = client.get(f"/api/v1/vault/host/items/{item_id}", headers=host_headers)
    assert owner.json()["body"] == "SECRET STUDIO BODY"
    assert any(m["url"] and not m["is_preview"] for m in owner.json()["media"])
    assert owner.json()["access"]["access_code"] is None


def test_vault_archive_and_ticket_scoped_access_rule(
    client: TestClient, db_session: Session
):
    host, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)

    category = db_session.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=3)
    event = Event(
        title="Scoped Night",
        slug="scoped-night-vault",
        description="Event for scoped vault access",
        host_id=host.id,
        category_id=category.id if category else None,
        status="published",
        start_datetime=start,
        end_datetime=start + timedelta(hours=4),
        city="Lagos",
        published_at=datetime.now(UTC),
    )
    db_session.add(event)
    db_session.flush()
    tt = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
        price=Decimal("2000.00"),
        quantity=100,
        quantity_sold=0,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=4,
        visibility="public",
        status="active",
    )
    db_session.add(tt)
    db_session.commit()

    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Scoped ticket drop",
            "content_type": "early_access",
            "preview_text": "Ticket scoped",
            "body": "SCOPED BODY",
            "status": "published",
            "access": {
                "access_type": "ticket_holder_only",
                "event_id": str(event.id),
                "ticket_type_ids": [str(tt.id)],
                "require_check_in": False,
            },
            "media": [],
        },
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]
    assert created.json()["access"]["event_id"] == str(event.id)

    archived = client.post(
        f"/api/v1/vault/host/items/{item_id}/archive",
        headers=host_headers,
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "archived"

    public = client.get("/api/v1/vault/public/vault-host/scoped-ticket-drop")
    assert public.status_code == 404


def test_vault_item_types_and_metadata_fields(client: TestClient, db_session: Session):
    _, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)
    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Private sponsor link",
            "content_type": "external_link",
            "description": "Public blurb",
            "preview_text": "Teaser only",
            "body": "SECRET NOTE",
            "external_url": "https://example.com/private",
            "file_url": "https://cdn.example.com/bonus.pdf",
            "tags": ["sponsor", "vip"],
            "status": "published",
            "access": {"access_type": "followers_only"},
            "media": [],
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["content_type"] == "external_link"
    assert body["description"] == "Public blurb"
    assert body["external_url"] == "https://example.com/private"
    assert body["file_url"] == "https://cdn.example.com/bonus.pdf"
    assert body["tags"] == ["sponsor", "vip"]
    assert body["expired"] is False

    public = client.get(f"/api/v1/vault/public/vault-host/{body['slug']}")
    assert public.status_code == 200
    locked = public.json()
    assert locked["locked"] is True
    assert locked["description"] == "Public blurb"
    assert locked["preview_text"] == "Teaser only"
    assert locked["body"] is None
    assert locked["external_url"] is None
    assert locked["file_url"] is None
    assert locked["tags"] == ["sponsor", "vip"]

    announcement = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Door note",
            "content_type": "announcement",
            "preview_text": "Fans only",
            "body": "Arrive by 9",
            "status": "published",
            "access": {"access_type": "free"},
            "media": [],
        },
    )
    assert announcement.status_code == 201, announcement.text
    assert announcement.json()["content_type"] == "announcement"


def test_invite_only_redeem_and_admin_hidden(client: TestClient, db_session: Session):
    _, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)

    invite = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Invite drop",
            "content_type": "announcement",
            "preview_text": "Code gated",
            "body": "INVITE BODY",
            "status": "published",
            "access": {
                "access_type": "invite_only",
                "access_code": "SECRET-VIP",
                "price": "0",
                "currency": "NGN",
            },
            "media": [],
        },
    )
    assert invite.status_code == 201, invite.text
    item_id = invite.json()["id"]
    slug = invite.json()["slug"]
    # Access codes are hashed at rest and never returned by the API
    assert invite.json()["access"]["access_code"] is None
    assert invite.json()["access"]["access_code_set"] is True

    buyer = _register(client, "invite-fan@example.com")
    locked = client.get(f"/api/v1/vault/public/vault-host/{slug}", headers=buyer)
    assert locked.status_code == 200
    assert locked.json()["locked"] is True
    assert locked.json()["body"] is None
    assert locked.json()["file_url"] is None
    assert locked.json()["external_url"] is None
    assert locked.json()["access"]["access_code"] is None
    assert locked.json()["access"]["access_code_set"] is True
    assert locked.json()["description"] is None  # invite-only: preview only

    bad = client.post(
        f"/api/v1/vault/redeem/{item_id}",
        headers=buyer,
        json={"access_code": "WRONG"},
    )
    assert bad.status_code == 403

    ok = client.post(
        f"/api/v1/vault/redeem/{item_id}",
        headers=buyer,
        json={"access_code": "SECRET-VIP"},
    )
    assert ok.status_code == 201, ok.text
    assert ok.json()["locked"] is False
    assert ok.json()["body"] == "INVITE BODY"

    hidden = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Hidden drop",
            "content_type": "text_post",
            "preview_text": "Nope",
            "body": "HIDDEN",
            "status": "published",
            "access": {"access_type": "admin_hidden", "price": "0"},
            "media": [],
        },
    )
    assert hidden.status_code == 201, hidden.text
    hidden_slug = hidden.json()["slug"]

    catalog = client.get("/api/v1/vault/public/vault-host")
    assert catalog.status_code == 200
    assert all(row["slug"] != hidden_slug for row in catalog.json())

    public_hidden = client.get(f"/api/v1/vault/public/vault-host/{hidden_slug}")
    assert public_hidden.status_code == 404


def test_checked_in_attendee_only(client: TestClient, db_session: Session):
    host, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)
    from app.payments.models import Order, OrderItem

    buyer = User(
        email="checked-fan@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Checked Fan",
        is_active=True,
    )
    buyer.roles.append(get_role_by_name(db_session, "buyer"))
    db_session.add(buyer)
    db_session.flush()

    category = db_session.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=2)
    event = Event(
        title="Check-in Night",
        slug="checkin-night",
        description="Event for checked-in vault access tests with enough detail.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=4),
        city="Lagos",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
    )
    db_session.add(event)
    db_session.flush()
    tt = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
        price=Decimal("2000.00"),
        quantity=100,
        quantity_sold=1,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=4,
        visibility="public",
        status="active",
    )
    db_session.add(tt)
    db_session.flush()
    order = Order(
        reference="PDY-VAULT-CHK",
        buyer_user_id=buyer.id,
        event_id=event.id,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("2000.00"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("2000.00"),
        buyer_email=buyer.email,
        buyer_name=buyer.full_name,
        paid_at=datetime.now(UTC),
    )
    db_session.add(order)
    db_session.flush()
    order_item = OrderItem(
        order_id=order.id,
        ticket_type_id=tt.id,
        quantity=1,
        unit_price=Decimal("2000.00"),
        line_total=Decimal("2000.00"),
        ticket_type_name=tt.name,
    )
    db_session.add(order_item)
    db_session.flush()
    ticket = Ticket(
        public_code=new_public_ticket_code(),
        order_id=order.id,
        order_item_id=order_item.id,
        event_id=event.id,
        ticket_type_id=tt.id,
        buyer_user_id=buyer.id,
        status="active",
        ticket_type_name=tt.name,
        holder_name=buyer.full_name,
        holder_email=buyer.email,
    )
    db_session.add(ticket)
    db_session.commit()

    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Door recap",
            "content_type": "ticket_holder_recap",
            "preview_text": "After check-in",
            "body": "CHECKED BODY",
            "status": "published",
            "access": {
                "access_type": "checked_in_attendee_only",
                "required_event_id": str(event.id),
                "price": "0",
            },
            "media": [],
        },
    )
    assert created.status_code == 201, created.text
    slug = created.json()["slug"]

    buyer_headers = _login(client, "checked-fan@example.com")
    locked = client.get(f"/api/v1/vault/public/vault-host/{slug}", headers=buyer_headers)
    assert locked.json()["locked"] is True
    assert locked.json()["access_reason"] == "check_in_required"

    ticket.status = "checked_in"
    db_session.commit()

    unlocked = client.get(f"/api/v1/vault/public/vault-host/{slug}", headers=buyer_headers)
    assert unlocked.json()["locked"] is False
    assert unlocked.json()["body"] == "CHECKED BODY"


def test_public_catalog_and_detail_never_leak_secrets(client: TestClient, db_session: Session):
    _, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)
    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Paid gallery",
            "content_type": "image_gallery",
            "description": "Public description",
            "preview_text": "Teaser",
            "body": "SECRET GALLERY BODY",
            "file_url": "https://cdn.example.com/secret.zip",
            "external_url": "https://example.com/private",
            "price": "1000.00",
            "status": "published",
            "access": {
                "access_type": "one_time_unlock",
                "price": "1000.00",
                "currency": "NGN",
            },
            "media": [
                {
                    "url": "https://cdn.example.com/preview.jpg",
                    "media_type": "image",
                    "is_preview": True,
                },
                {
                    "url": "https://cdn.example.com/private.jpg",
                    "media_type": "image",
                    "is_preview": False,
                },
            ],
        },
    )
    assert created.status_code == 201, created.text
    slug = created.json()["slug"]

    catalog = client.get("/api/v1/vault/public/vault-host")
    assert catalog.status_code == 200
    card = next(row for row in catalog.json() if row["slug"] == slug)
    assert "body" not in card
    assert "file_url" not in card
    assert "external_url" not in card
    assert "media" not in card
    assert card["preview_text"] == "Teaser"
    assert card["locked"] is True
    assert card["access_type"] == "one_time_unlock"
    assert card["content_type"] == "image_gallery"
    assert "featured" in card
    assert Decimal(card["price"]) == Decimal("1000.00")
    assert card["cta_label"]

    detail = client.get(f"/api/v1/vault/public/vault-host/{slug}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["locked"] is True
    assert body["body"] is None
    assert body["file_url"] is None
    assert body["external_url"] is None
    assert body["lock_reason"]
    assert all(m["url"] != "https://cdn.example.com/private.jpg" for m in body["media"])
    assert any(m["url"] == "https://cdn.example.com/preview.jpg" for m in body["media"])


def test_vault_item_lifecycle_publish_unpublish_schedule_restore_delete(
    client: TestClient, db_session: Session
):
    host, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)

    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Lifecycle drop",
            "content_type": "text_post",
            "preview_text": "Teaser",
            "body": "Secret body",
            "status": "draft",
            "access": {"access_type": "free"},
            "media": [],
        },
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]
    assert created.json()["status"] == "draft"

    published = client.post(
        f"/api/v1/vault/host/items/{item_id}/publish",
        headers=host_headers,
    )
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "published"

    unpublished = client.post(
        f"/api/v1/vault/host/items/{item_id}/unpublish",
        headers=host_headers,
    )
    assert unpublished.status_code == 200
    assert unpublished.json()["status"] == "draft"

    starts = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    # Need access rule starts_at via update first, then schedule
    patched = client.patch(
        f"/api/v1/vault/host/items/{item_id}",
        headers=host_headers,
        json={"access": {"access_type": "free", "starts_at": starts}},
    )
    assert patched.status_code == 200, patched.text
    scheduled = client.post(
        f"/api/v1/vault/host/items/{item_id}/schedule",
        headers=host_headers,
        json={"starts_at": starts},
    )
    assert scheduled.status_code == 200, scheduled.text
    assert scheduled.json()["status"] == "scheduled"

    archived = client.post(
        f"/api/v1/vault/host/items/{item_id}/archive",
        headers=host_headers,
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert archived.json()["archived_at"] is not None

    restored = client.post(
        f"/api/v1/vault/host/items/{item_id}/restore",
        headers=host_headers,
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "draft"

    deleted = client.delete(
        f"/api/v1/vault/host/items/{item_id}",
        headers=host_headers,
    )
    assert deleted.status_code == 200, deleted.text


def test_vault_delete_blocked_with_paid_unlock(
    client: TestClient, db_session: Session
):
    host, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)
    buyer_headers = _register(client, "vault-buyer-lifecycle@example.com", "Buyer")

    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Paid lifecycle",
            "content_type": "text_post",
            "preview_text": "Teaser",
            "body": "Paid body",
            "status": "published",
            "access": {
                "access_type": "one_time_unlock",
                "price": "500.00",
                "currency": "NGN",
            },
            "media": [],
        },
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]

    with patch(
        "app.vault.service.initialize_transaction",
        return_value={
            "authorization_url": "https://pay.example/checkout",
            "access_code": "access",
        },
    ):
        unlock = client.post(
            f"/api/v1/vault/unlock/{item_id}",
            headers=buyer_headers,
        )
    assert unlock.status_code == 201, unlock.text
    reference = unlock.json()["purchase"]["payment_reference"]
    purchase = get_vault_purchase_by_reference(db_session, reference)
    assert purchase is not None
    finalize_vault_purchase(
        db_session,
        purchase=purchase,
        provider_payment_id="pay_life_1",
        raw_payload={"ok": True},
        actor_user_id=purchase.user_id,
    )
    db_session.commit()

    # Published with history cannot hard-delete
    blocked = client.delete(
        f"/api/v1/vault/host/items/{item_id}",
        headers=host_headers,
    )
    assert blocked.status_code == 400
    assert "draft" in blocked.json()["detail"].lower() or "archive" in blocked.json()["detail"].lower()

    # Unpublish then still blocked due to purchase history
    client.post(f"/api/v1/vault/host/items/{item_id}/unpublish", headers=host_headers)
    blocked_draft = client.delete(
        f"/api/v1/vault/host/items/{item_id}",
        headers=host_headers,
    )
    assert blocked_draft.status_code == 400
    assert "archive" in blocked_draft.json()["detail"].lower()

    archived = client.post(
        f"/api/v1/vault/host/items/{item_id}/archive",
        headers=host_headers,
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"


def test_admin_hide_and_restore_vault_item(
    client: TestClient, db_session: Session, assign_role
):
    host, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)
    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Hide me",
            "content_type": "text_post",
            "preview_text": "Teaser",
            "body": "Body",
            "status": "published",
            "access": {"access_type": "free"},
            "media": [],
        },
    )
    item_id = created.json()["id"]
    slug = created.json()["slug"]

    _register(client, "vault-hide-mod@example.com", "Mod")
    assign_role("vault-hide-mod@example.com", "finance_admin")
    admin_headers = _login(client, "vault-hide-mod@example.com")

    hidden = client.post(
        f"/api/v1/vault/admin/items/{item_id}/moderate",
        headers=admin_headers,
        json={"action": "hide", "note": "policy"},
    )
    assert hidden.status_code == 200, hidden.text
    assert hidden.json()["status"] == "hidden_by_admin"

    public = client.get(f"/api/v1/vault/public/vault-host/{slug}")
    assert public.status_code == 404

    # Host cannot edit while hidden
    edit = client.patch(
        f"/api/v1/vault/host/items/{item_id}",
        headers=host_headers,
        json={"title": "Nope"},
    )
    assert edit.status_code == 403

    restored = client.post(
        f"/api/v1/vault/admin/items/{item_id}/moderate",
        headers=admin_headers,
        json={"action": "restore", "note": "cleared after review"},
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "published"
    assert restored.json()["moderation_status"] == "approved"
    assert restored.json()["moderation_note"] == "cleared after review"


def test_admin_vault_filters_summary_and_support_blocked(
    client: TestClient, db_session: Session, assign_role
):
    from app.core.audit import AuditLog
    from sqlalchemy import select

    host, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)
    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Paid admin summary",
            "content_type": "video",
            "preview_text": "Teaser",
            "body": "SECRET",
            "price": "2000.00",
            "status": "published",
            "access": {"access_type": "one_time_unlock"},
            "media": [],
        },
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]

    buyer = _register(client, "vault-admin-sum-buyer@example.com")
    with patch(
        "app.vault.service.initialize_transaction",
        return_value={
            "authorization_url": "https://paystack.test/auth",
            "access_code": "ACCESS",
        },
    ):
        checkout = client.post(f"/api/v1/vault/unlock/{item_id}", headers=buyer)
    reference = checkout.json()["purchase"]["payment_reference"]
    purchase = get_vault_purchase_by_reference(db_session, reference)
    assert purchase is not None
    finalize_vault_purchase(
        db_session,
        purchase=purchase,
        provider_payment_id="pay_admin_sum",
        raw_payload={"ok": True},
        actor_user_id=purchase.user_id,
    )
    db_session.commit()

    _register(client, "vault-admin-filter@example.com", "Admin")
    assign_role("vault-admin-filter@example.com", "finance_admin")
    admin = _login(client, "vault-admin-filter@example.com")

    listed = client.get(
        "/api/v1/vault/admin/items",
        headers=admin,
        params={
            "access_type": "one_time_unlock",
            "host_username": "vault-host",
            "status": "published",
            "q": "Paid admin",
        },
    )
    assert listed.status_code == 200, listed.text
    rows = listed.json()
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == item_id
    assert row["access_type"] == "one_time_unlock"
    assert row["unlock_count"] == 1
    assert row["paid_purchase_count"] == 1
    assert Decimal(row["gross_revenue"]) == Decimal("2000.00")
    assert row["report_count"] == 0

    no_reason = client.post(
        f"/api/v1/vault/admin/items/{item_id}/moderate",
        headers=admin,
        json={"action": "archive"},
    )
    assert no_reason.status_code == 400

    archived = client.post(
        f"/api/v1/vault/admin/items/{item_id}/moderate",
        headers=admin,
        json={"action": "archive", "note": "Spam drop"},
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "archived"
    assert archived.json()["moderation_status"] == "removed"
    assert archived.json()["moderation_note"] == "Spam drop"

    audit = db_session.scalar(
        select(AuditLog)
        .where(
            AuditLog.action == "vault.moderate.archive",
            AuditLog.resource_id == item_id,
        )
        .order_by(AuditLog.created_at.desc())
    )
    assert audit is not None
    assert (audit.details or {}).get("note") == "Spam drop"

    _register(client, "vault-support-blocked@example.com", "Support")
    assign_role("vault-support-blocked@example.com", "support_agent")
    support = _login(client, "vault-support-blocked@example.com")
    blocked_list = client.get("/api/v1/vault/admin/items", headers=support)
    assert blocked_list.status_code == 403
    blocked_mod = client.post(
        f"/api/v1/vault/admin/items/{item_id}/moderate",
        headers=support,
        json={"action": "restore", "note": "should fail"},
    )
    assert blocked_mod.status_code == 403


def test_buyer_vault_library_includes_purchased_with_access_label(
    client: TestClient, db_session: Session
):
    host, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)
    buyer = _register(client, "vault-library-buyer@example.com")

    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Library paid drop",
            "content_type": "text_post",
            "preview_text": "Teaser",
            "body": "Paid body",
            "status": "published",
            "access": {
                "access_type": "one_time_unlock",
                "price": "1500.00",
                "currency": "NGN",
            },
            "media": [],
        },
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]

    with patch(
        "app.vault.service.initialize_transaction",
        return_value={
            "authorization_url": "https://pay.example/checkout",
            "access_code": "access",
        },
    ):
        unlock = client.post(f"/api/v1/vault/unlock/{item_id}", headers=buyer)
    assert unlock.status_code == 201, unlock.text
    reference = unlock.json()["purchase"]["payment_reference"]
    purchase = get_vault_purchase_by_reference(db_session, reference)
    assert purchase is not None
    finalize_vault_purchase(
        db_session,
        purchase=purchase,
        provider_payment_id="pay_lib_1",
        raw_payload={"ok": True},
        actor_user_id=purchase.user_id,
    )
    db_session.commit()

    library = client.get("/api/v1/vault/me/library", headers=buyer)
    assert library.status_code == 200, library.text
    body = library.json()
    assert body["stats"]["unlocked_count"] >= 1
    assert body["stats"]["purchase_count"] >= 1
    unlocked = next(i for i in body["unlocked"] if i["id"] == item_id)
    assert unlocked["has_access"] is True
    assert unlocked["access_reason"] == "purchased"
    assert unlocked["access_label"] == "Purchased"
    assert any(a["kind"] in {"purchase", "access"} for a in body["activity"])


def test_vault_unlock_webhook_idempotent_no_tickets(
    client: TestClient, db_session: Session
):
    import json

    from sqlalchemy import func, select

    from app.finance.models import LedgerEntry
    from app.payments.paystack import sign_body_for_tests
    from app.tickets.models import Ticket
    from app.vault.models import VaultAccessGrant, VaultPurchase

    _, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)
    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Paid drop webhook",
            "content_type": "video",
            "preview_text": "Pay to unlock",
            "body": "SECRET PAID BODY",
            "price": "1500.00",
            "status": "published",
            "access": {"access_type": "one_time_unlock"},
            "media": [],
        },
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]
    slug = created.json()["slug"]

    buyer = _register(client, "vault-wh-buyer@example.com")
    with patch(
        "app.vault.service.initialize_transaction",
        return_value={
            "authorization_url": "https://paystack.test/auth",
            "access_code": "ACCESS",
        },
    ):
        checkout = client.post(f"/api/v1/vault/unlock/{item_id}", headers=buyer)
    assert checkout.status_code == 201, checkout.text
    purchase_id = checkout.json()["purchase"]["id"]
    reference = checkout.json()["purchase"]["payment_reference"]
    assert reference.startswith("PDY-VLT-")
    assert checkout.json()["purchase"]["status"] == "pending"

    # Reuse pending checkout instead of creating a second payment row
    with patch(
        "app.vault.service.initialize_transaction",
        return_value={
            "authorization_url": "https://paystack.test/auth",
            "access_code": "ACCESS",
        },
    ):
        again = client.post(f"/api/v1/vault/unlock/{item_id}", headers=buyer)
    assert again.status_code == 201
    assert again.json()["purchase"]["id"] == purchase_id

    payload = {
        "event": "charge.success",
        "data": {
            "id": 777001,
            "reference": reference,
            "amount": 150000,
            "status": "success",
        },
    }
    body = json.dumps(payload).encode("utf-8")
    signature = sign_body_for_tests(body)
    headers_wh = {
        "x-paystack-signature": signature,
        "content-type": "application/json",
    }

    first = client.post(
        "/api/v1/payments/webhooks/paystack", content=body, headers=headers_wh
    )
    second = client.post(
        "/api/v1/payments/webhooks/paystack", content=body, headers=headers_wh
    )
    assert first.status_code == 200, first.text
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"

    from uuid import UUID

    item_uuid = UUID(item_id)
    db_session.expire_all()
    paid = db_session.scalars(
        select(VaultPurchase).where(
            VaultPurchase.vault_item_id == item_uuid,
            VaultPurchase.status == "paid",
        )
    ).all()
    assert len(paid) == 1

    grants = db_session.scalars(
        select(VaultAccessGrant).where(VaultAccessGrant.vault_item_id == item_uuid)
    ).all()
    assert len(grants) == 1

    ledger_count = db_session.scalar(
        select(func.count())
        .select_from(LedgerEntry)
        .where(
            LedgerEntry.entry_type == "vault_sale",
            LedgerEntry.reference_type == "vault_purchase",
            LedgerEntry.reference_id == purchase_id,
        )
    )
    assert int(ledger_count or 0) == 1

    # Vault unlocks never issue event tickets
    tickets = db_session.scalars(select(Ticket)).all()
    assert tickets == []

    unlocked = client.get(f"/api/v1/vault/public/vault-host/{slug}", headers=buyer)
    assert unlocked.status_code == 200
    assert unlocked.json()["locked"] is False
    assert unlocked.json()["body"] == "SECRET PAID BODY"
    assert unlocked.json()["access_reason"] == "purchased"

    # Double finalize is a no-op for ledger/grant
    purchase = get_vault_purchase_by_reference(db_session, reference)
    assert purchase is not None
    finalize_vault_purchase(
        db_session,
        purchase=purchase,
        provider_payment_id="pay_retry",
        raw_payload={"retry": True},
        actor_user_id=purchase.user_id,
    )
    db_session.commit()
    ledger_count_after = db_session.scalar(
        select(func.count())
        .select_from(LedgerEntry)
        .where(
            LedgerEntry.entry_type == "vault_sale",
            LedgerEntry.reference_id == purchase_id,
        )
    )
    assert int(ledger_count_after or 0) == 1
    assert (
        db_session.scalar(
            select(func.count()).select_from(VaultAccessGrant).where(
                VaultAccessGrant.vault_item_id == item_uuid
            )
        )
        == 1
    )

    earnings = client.get("/api/v1/vault/host/earnings", headers=host_headers)
    assert earnings.status_code == 200
    assert Decimal(earnings.json()["gross_revenue"]) == Decimal("1500.00")
    assert earnings.json()["paid_purchase_count"] == 1


def test_demo_mode_vault_unlock_mocked(
    client: TestClient, db_session: Session, monkeypatch
):
    from app.core.config import get_settings

    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()

    try:
        _, host_user = _seed_host(db_session)
        host_headers = _login(client, host_user.email)
        created = client.post(
            "/api/v1/vault/host/items",
            headers=host_headers,
            json={
                "title": "Demo unlock drop",
                "content_type": "text_post",
                "preview_text": "Demo",
                "body": "DEMO BODY",
                "price": "999.00",
                "status": "published",
                "access": {"access_type": "one_time_unlock"},
                "media": [],
            },
        )
        assert created.status_code == 201, created.text
        item_id = created.json()["id"]
        slug = created.json()["slug"]
        buyer = _register(client, "vault-demo-buyer@example.com")

        checkout = client.post(f"/api/v1/vault/unlock/{item_id}", headers=buyer)
        assert checkout.status_code == 201, checkout.text
        assert checkout.json()["purchase"]["status"] == "paid"
        assert checkout.json()["purchase"]["authorization_url"] is None

        unlocked = client.get(f"/api/v1/vault/public/vault-host/{slug}", headers=buyer)
        assert unlocked.json()["locked"] is False
        assert unlocked.json()["body"] == "DEMO BODY"
    finally:
        monkeypatch.setenv("DEMO_MODE", "false")
        monkeypatch.setenv("APP_ENV", "test")
        get_settings.cache_clear()


def test_vault_related_to_event_and_memory(client: TestClient, db_session: Session):
    from app.memories.models import EventMemory

    host, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)

    category = db_session.query(EventCategory).first()
    start = datetime.now(UTC) - timedelta(days=2)
    event = Event(
        title="Recap Night",
        slug="recap-night",
        description="Event used for Vault related reverse lookups.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        city="Lagos",
        status="published",
        featured=False,
        published_at=start,
    )
    db_session.add(event)
    db_session.flush()
    memory = EventMemory(
        event_id=event.id,
        host_id=host.id,
        status="published",
        host_recap_note="Great night",
        moderation_status="none",
        published_at=datetime.now(UTC),
    )
    db_session.add(memory)
    db_session.commit()

    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Afterparty recap",
            "content_type": "ticket_holder_recap",
            "preview_text": "Unlock after the show",
            "body": "SECRET RECAP BODY",
            "status": "published",
            "related_event_id": str(event.id),
            "related_memory_id": str(memory.id),
            "access": {
                "access_type": "ticket_holder_only",
                "required_event_id": str(event.id),
            },
            "media": [],
        },
    )
    assert created.status_code == 201, created.text
    item = created.json()
    assert item["related_event"]["slug"] == "recap-night"
    assert item["related_memory"]["event_slug"] == "recap-night"
    assert item["related_memory"]["href"].endswith("/memories/recap-night")

    by_event = client.get(f"/api/v1/vault/related/event/{event.id}")
    assert by_event.status_code == 200, by_event.text
    event_cards = by_event.json()
    assert len(event_cards) == 1
    assert event_cards[0]["id"] == item["id"]
    assert event_cards[0]["locked"] is True
    assert "SECRET RECAP BODY" not in str(event_cards)
    assert "body" not in event_cards[0]

    by_memory = client.get(f"/api/v1/vault/related/memory/{memory.id}")
    assert by_memory.status_code == 200, by_memory.text
    memory_cards = by_memory.json()
    assert len(memory_cards) == 1
    assert memory_cards[0]["id"] == item["id"]

    public = client.get(f"/api/v1/vault/public/vault-host/{item['slug']}")
    assert public.status_code == 200
    detail = public.json()
    assert detail["related_event"]["title"] == "Recap Night"
    assert detail["related_memory"]["event_title"] == "Recap Night"
    assert detail["body"] is None
    assert "SECRET RECAP BODY" not in str(detail)


# ---------------------------------------------------------------------------
# Checklist coverage — ownership, access matrix, visibility, Legacy redaction
# Also covered by earlier tests in this module (see names in comments).
# ---------------------------------------------------------------------------


def test_host_creates_vault_item(client: TestClient, db_session: Session):
    """Host can create a published Vault item (see also test_create_and_access_free_item)."""
    _, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)
    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Host created drop",
            "content_type": "text_post",
            "preview_text": "Preview",
            "body": "Created body content",
            "status": "published",
            "access": {"access_type": "free"},
            "media": [],
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["title"] == "Host created drop"
    assert created.json()["has_access"] is True


def test_public_list_redacts_locked_content(client: TestClient, db_session: Session):
    """Public catalog never includes locked body/media (see also test_public_catalog...)."""
    _, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)
    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Catalog redact",
            "content_type": "video",
            "preview_text": "Teaser ok",
            "body": "CATALOG SECRET",
            "status": "published",
            "access": {"access_type": "one_time_unlock", "price": "1000"},
            "media": [
                {
                    "url": "https://cdn.example.com/catalog-secret.mp4",
                    "media_type": "video",
                    "is_preview": False,
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    catalog = client.get("/api/v1/vault/public/vault-host")
    assert catalog.status_code == 200
    payload = catalog.json()
    assert any(row["slug"] == created.json()["slug"] for row in payload)
    assert "CATALOG SECRET" not in str(payload)
    assert "catalog-secret.mp4" not in str(payload)
    assert all("body" not in row for row in payload)


def test_public_detail_redacts_locked_content(client: TestClient, db_session: Session):
    """Public detail redacts locked fields (see also test_block_locked_item_without_access)."""
    _, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)
    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Detail redact",
            "content_type": "text_post",
            "preview_text": "Teaser",
            "body": "DETAIL SECRET",
            "file_url": "https://cdn.example.com/secret.pdf",
            "status": "published",
            "access": {"access_type": "followers_only"},
            "media": [],
        },
    )
    assert created.status_code == 201, created.text
    slug = created.json()["slug"]
    detail = client.get(f"/api/v1/vault/public/vault-host/{slug}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["locked"] is True
    assert body["body"] is None
    assert body["file_url"] is None
    assert "DETAIL SECRET" not in str(body)


def test_ticket_holder_access_works(client: TestClient, db_session: Session):
    """Alias entry-point — full matrix in test_ticket_holder_access_and_block."""
    test_ticket_holder_access_and_block(client, db_session)


def test_checked_in_attendee_access_works(client: TestClient, db_session: Session):
    """Alias entry-point — full matrix in test_checked_in_attendee_only."""
    test_checked_in_attendee_only(client, db_session)


def test_one_time_unlock_access_works(client: TestClient, db_session: Session):
    """Alias entry-point — full matrix in test_one_time_unlock_purchase."""
    test_one_time_unlock_purchase(client, db_session)


def test_invite_only_access_works(client: TestClient, db_session: Session):
    """Alias entry-point — full matrix in test_invite_only_redeem_and_admin_hidden."""
    test_invite_only_redeem_and_admin_hidden(client, db_session)


def test_archived_item_not_public(client: TestClient, db_session: Session):
    _, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)
    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Archive me",
            "slug": "archive-me",
            "content_type": "text_post",
            "preview_text": "Teaser",
            "body": "ARCHIVE SECRET",
            "status": "published",
            "access": {"access_type": "free"},
            "media": [],
        },
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]
    archived = client.post(
        f"/api/v1/vault/host/items/{item_id}/archive",
        headers=host_headers,
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    catalog = client.get("/api/v1/vault/public/vault-host")
    assert all(row["slug"] != "archive-me" for row in catalog.json())
    assert client.get("/api/v1/vault/public/vault-host/archive-me").status_code == 404


def test_admin_hidden_item_not_public(
    client: TestClient, db_session: Session, assign_role
):
    _, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)
    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Hide me",
            "slug": "hide-me",
            "content_type": "text_post",
            "preview_text": "Teaser",
            "body": "HIDDEN SECRET",
            "status": "published",
            "access": {"access_type": "free"},
            "media": [],
        },
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]

    _register(client, "vault-checklist-mod@example.com", "Checklist Mod")
    assign_role("vault-checklist-mod@example.com", "finance_admin")
    admin_headers = _login(client, "vault-checklist-mod@example.com")
    hidden = client.post(
        f"/api/v1/vault/admin/items/{item_id}/moderate",
        headers=admin_headers,
        json={"action": "hide", "note": "Checklist hide"},
    )
    assert hidden.status_code == 200, hidden.text

    catalog = client.get("/api/v1/vault/public/vault-host")
    assert all(row["slug"] != "hide-me" for row in catalog.json())
    assert client.get("/api/v1/vault/public/vault-host/hide-me").status_code == 404


def test_paid_unlocked_item_cannot_be_hard_deleted(
    client: TestClient, db_session: Session
):
    """Alias — full matrix in test_vault_delete_blocked_with_paid_unlock."""
    test_vault_delete_blocked_with_paid_unlock(client, db_session)


def test_draft_item_can_be_deleted(client: TestClient, db_session: Session):
    _, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)
    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Delete draft",
            "content_type": "text_post",
            "preview_text": "Teaser",
            "body": "Draft only",
            "status": "draft",
            "access": {"access_type": "free"},
            "media": [],
        },
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]
    deleted = client.delete(
        f"/api/v1/vault/host/items/{item_id}",
        headers=host_headers,
    )
    assert deleted.status_code == 200, deleted.text
    assert (
        client.get(f"/api/v1/vault/host/items/{item_id}", headers=host_headers).status_code
        == 404
    )


def test_admin_moderation_works(
    client: TestClient, db_session: Session, assign_role
):
    """Alias — full matrix in test_admin_moderation / test_admin_hide_and_restore."""
    test_admin_moderation(client, db_session, assign_role)


def test_host_edits_own_vault_item(client: TestClient, db_session: Session):
    _, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)

    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Editable drop",
            "content_type": "text_post",
            "preview_text": "Old preview",
            "body": "Old body content here",
            "status": "published",
            "access": {"access_type": "free"},
            "media": [],
        },
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]

    patched = client.patch(
        f"/api/v1/vault/host/items/{item_id}",
        headers=host_headers,
        json={
            "title": "Edited drop title",
            "preview_text": "Updated preview",
            "body": "Updated exclusive body content",
        },
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["title"] == "Edited drop title"
    assert patched.json()["preview_text"] == "Updated preview"
    assert patched.json()["body"] == "Updated exclusive body content"

    public = client.get("/api/v1/vault/public/vault-host/editable-drop")
    assert public.status_code == 200
    assert public.json()["title"] == "Edited drop title"
    assert public.json()["body"] == "Updated exclusive body content"


def test_host_cannot_edit_another_hosts_vault_item(
    client: TestClient, db_session: Session
):
    _, owner = _seed_host(db_session)
    owner_headers = _login(client, owner.email)
    _, other = _seed_host(
        db_session,
        email="vault-host-b@example.com",
        slug="vault-host-b",
        display_name="Vault Host B",
    )
    other_headers = _login(client, other.email)

    created = client.post(
        "/api/v1/vault/host/items",
        headers=owner_headers,
        json={
            "title": "Owner only drop",
            "content_type": "text_post",
            "preview_text": "Preview",
            "body": "OWNER SECRET BODY",
            "status": "published",
            "access": {"access_type": "free"},
            "media": [],
        },
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]

    denied = client.patch(
        f"/api/v1/vault/host/items/{item_id}",
        headers=other_headers,
        json={"title": "Hijacked title", "body": "Hijacked body"},
    )
    assert denied.status_code == 404, denied.text

    still = client.get(f"/api/v1/vault/host/items/{item_id}", headers=owner_headers)
    assert still.status_code == 200
    assert still.json()["title"] == "Owner only drop"
    assert still.json()["body"] == "OWNER SECRET BODY"


def test_followers_only_access_works(client: TestClient, db_session: Session):
    _, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)
    fan_headers = _register(client, "vault-follower@example.com", "Vault Follower")

    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Followers unlock",
            "content_type": "vip_content",
            "preview_text": "Teaser",
            "body": "FOLLOWER BODY",
            "status": "published",
            "access": {"access_type": "followers_only"},
            "media": [
                {
                    "url": "https://cdn.example.com/private-follow.mp4",
                    "media_type": "video",
                    "is_preview": False,
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    slug = created.json()["slug"]

    before = client.get(f"/api/v1/vault/public/vault-host/{slug}", headers=fan_headers)
    assert before.status_code == 200
    assert before.json()["locked"] is True
    assert before.json()["access_reason"] == "followers_only"
    assert before.json()["body"] is None
    assert "FOLLOWER BODY" not in str(before.json())

    followed = client.post(
        "/api/v1/crm/follow",
        headers=fan_headers,
        json={"host_slug": "vault-host"},
    )
    assert followed.status_code == 201, followed.text

    after = client.get(f"/api/v1/vault/public/vault-host/{slug}", headers=fan_headers)
    assert after.status_code == 200
    assert after.json()["locked"] is False
    assert after.json()["body"] == "FOLLOWER BODY"
    urls = [m["url"] for m in after.json()["media"]]
    assert "https://cdn.example.com/private-follow.mp4" in urls


def test_vip_ticket_holder_access_works(client: TestClient, db_session: Session):
    host, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)
    from app.payments.models import Order, OrderItem

    vip_buyer = User(
        email="vip-fan@example.com",
        password_hash=hash_password("securepass1"),
        full_name="VIP Fan",
        is_active=True,
    )
    vip_buyer.roles.append(get_role_by_name(db_session, "buyer"))
    ga_buyer = User(
        email="ga-fan@example.com",
        password_hash=hash_password("securepass1"),
        full_name="GA Fan",
        is_active=True,
    )
    ga_buyer.roles.append(get_role_by_name(db_session, "buyer"))
    db_session.add_all([vip_buyer, ga_buyer])
    db_session.flush()

    category = db_session.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=3)
    event = Event(
        title="VIP Vault Night",
        slug="vip-vault-night",
        description="Event for VIP vault ticket holder access tests with detail.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        city="Lagos",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
    )
    db_session.add(event)
    db_session.flush()
    vip_tt = TicketType(
        event_id=event.id,
        name="VIP",
        type="vip",
        price=Decimal("15000.00"),
        quantity=20,
        quantity_sold=1,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=2,
        visibility="public",
        status="active",
    )
    ga_tt = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
        price=Decimal("3000.00"),
        quantity=100,
        quantity_sold=1,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=4,
        visibility="public",
        status="active",
    )
    db_session.add_all([vip_tt, ga_tt])
    db_session.flush()

    for buyer, tt, ref in (
        (vip_buyer, vip_tt, "PDY-VAULT-VIP"),
        (ga_buyer, ga_tt, "PDY-VAULT-GA"),
    ):
        order = Order(
            reference=ref,
            buyer_user_id=buyer.id,
            event_id=event.id,
            status="paid",
            currency="NGN",
            subtotal_amount=tt.price,
            discount_amount=Decimal("0"),
            total_amount=tt.price,
            buyer_email=buyer.email,
            buyer_name=buyer.full_name,
            paid_at=datetime.now(UTC),
        )
        db_session.add(order)
        db_session.flush()
        line = OrderItem(
            order_id=order.id,
            ticket_type_id=tt.id,
            quantity=1,
            unit_price=tt.price,
            line_total=tt.price,
            ticket_type_name=tt.name,
        )
        db_session.add(line)
        db_session.flush()
        db_session.add(
            Ticket(
                public_code=new_public_ticket_code(),
                order_id=order.id,
                order_item_id=line.id,
                event_id=event.id,
                ticket_type_id=tt.id,
                buyer_user_id=buyer.id,
                status="active",
                ticket_type_name=tt.name,
                holder_name=buyer.full_name,
                holder_email=buyer.email,
            )
        )
    db_session.commit()

    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "VIP lounge gallery",
            "content_type": "image_gallery",
            "preview_text": "VIP only",
            "body": "VIP SECRET GALLERY",
            "status": "published",
            "related_event_id": str(event.id),
            "access": {
                "access_type": "vip_ticket_holder_only",
                "required_event_id": str(event.id),
            },
            "media": [],
        },
    )
    assert created.status_code == 201, created.text
    slug = created.json()["slug"]

    vip_headers = _login(client, "vip-fan@example.com")
    unlocked = client.get(
        f"/api/v1/vault/public/vault-host/{slug}", headers=vip_headers
    )
    assert unlocked.status_code == 200
    assert unlocked.json()["locked"] is False
    assert unlocked.json()["body"] == "VIP SECRET GALLERY"

    ga_headers = _login(client, "ga-fan@example.com")
    blocked = client.get(f"/api/v1/vault/public/vault-host/{slug}", headers=ga_headers)
    assert blocked.status_code == 200
    assert blocked.json()["locked"] is True
    assert blocked.json()["access_reason"] == "vip_ticket_required"
    assert blocked.json()["body"] is None
    assert "VIP SECRET GALLERY" not in str(blocked.json())


def test_draft_item_not_public(client: TestClient, db_session: Session):
    _, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)

    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Draft secret drop",
            "slug": "draft-secret-drop",
            "content_type": "text_post",
            "preview_text": "Should not list",
            "body": "DRAFT SECRET BODY",
            "status": "draft",
            "access": {"access_type": "free"},
            "media": [],
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "draft"

    catalog = client.get("/api/v1/vault/public/vault-host")
    assert catalog.status_code == 200
    assert all(row["slug"] != "draft-secret-drop" for row in catalog.json())
    assert "DRAFT SECRET BODY" not in str(catalog.json())

    detail = client.get("/api/v1/vault/public/vault-host/draft-secret-drop")
    assert detail.status_code == 404


def test_legacy_vault_block_does_not_leak_locked_content(
    client: TestClient, db_session: Session
):
    _, host_user = _seed_host(db_session)
    host_headers = _login(client, host_user.email)

    created = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Legacy teaser drop",
            "content_type": "video",
            "preview_text": "Public teaser only",
            "body": "LEGACY LEAK BODY",
            "status": "published",
            "access": {"access_type": "one_time_unlock", "price": "2500"},
            "media": [
                {
                    "url": "https://cdn.example.com/legacy-private.mp4",
                    "media_type": "video",
                    "is_preview": False,
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]

    featured = client.post(
        "/api/v1/host/legacy/featured-items",
        headers=host_headers,
        json={
            "item_type": "vault_item",
            "item_id": item_id,
            "placement": "featured_vault_item",
        },
    )
    assert featured.status_code == 200, featured.text

    public = client.get("/api/v1/legacy/vault-host")
    assert public.status_code == 200, public.text
    body = public.json()
    assert body.get("vault_preview")
    card = body["vault_preview"][0]
    assert card["id"] == item_id
    assert card["locked"] is True
    assert card.get("has_access") is False
    assert "body" not in card
    assert "LEGACY LEAK BODY" not in str(body)
    assert "legacy-private.mp4" not in str(body)
