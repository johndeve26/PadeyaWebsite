"""Legacy Content Studio — page settings, blocks, featured items, public visibility."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile, HostVerification
from app.legacy.models import HostLegacyContentBlock, HostLegacyFeaturedItem
from app.legacy.studio import ensure_default_blocks, ensure_legacy_page
from app.payments.models import Order, OrderItem
from app.reviews.models import VerifiedReview
from app.tickets.models import Ticket
from app.tickets.qr import new_public_ticket_code
from app.users.models import User
from app.users.service import get_role_by_name
from app.vault.models import VaultAccessRule, VaultItem


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _make_host(
    db: Session,
    *,
    email: str,
    slug: str,
    display_name: str = "Studio Host",
) -> Host:
    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name=display_name,
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    user.roles.append(role)
    db.add(user)
    db.flush()
    host = Host(
        user_id=user.id,
        display_name=display_name,
        slug=slug,
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(
        HostProfile(
            host_id=host.id,
            bio="Studio bio",
            city="Lagos",
            avatar_url="https://cdn.example.com/a.jpg",
            cover_url="https://cdn.example.com/c.jpg",
        )
    )
    db.add(HostVerification(host_id=host.id, status="verified"))
    db.commit()
    return host


def test_host_can_update_own_legacy_page(client: TestClient, db_session: Session) -> None:
    host = _make_host(db_session, email="studio-a@example.com", slug="studio-a")
    headers = _login(client, "studio-a@example.com")

    res = client.patch(
        "/api/v1/host/legacy",
        headers=headers,
        json={
            "display_name": "Studio A Updated",
            "tagline": "Nights that travel",
            "sponsorship_available": True,
            "primary_cta_label": "Book a night",
            "primary_cta_type": "events",
            "primary_cta_value": "#upcoming-events",
            "social_links": [
                {"platform": "instagram", "url": "https://instagram.com/studioa"}
            ],
            "contact": {
                "preference": "email",
                "public_email": "book@studioa.test",
                "show_contact_form": False,
            },
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["display_name"] == "Studio A Updated"
    assert body["tagline"] == "Nights that travel"
    assert body["settings"]["sponsorship_available"] is True
    assert body["settings"]["primary_cta_label"] == "Book a night"
    assert any(s["platform"] == "instagram" for s in body["social_links"])
    assert body["contact"]["public_email"] == "book@studioa.test"
    assert len(body["content_blocks"]) >= 8
    assert str(host.id) == body["host_id"]


def test_host_can_save_legacy_profile_with_roundtripped_contact(
    client: TestClient, db_session: Session
) -> None:
    """Studio edit reloads contact (id/host_id) from GET — PATCH must not 500 on audit."""
    _make_host(db_session, email="studio-contact@example.com", slug="Padeya")
    headers = _login(client, "studio-contact@example.com")

    loaded = client.get("/api/v1/host/legacy", headers=headers)
    assert loaded.status_code == 200, loaded.text
    contact = loaded.json()["contact"]
    assert contact is not None
    assert contact.get("id")

    res = client.patch(
        "/api/v1/host/legacy",
        headers=headers,
        json={
            "display_name": "Padeya",
            "username": "Padeya",
            "service_areas": [],
            "sponsorship_available": False,
            "social_links": [],
            "contact": contact,
        },
    )
    assert res.status_code == 200, res.text
    assert res.json()["username"] == "padeya"


def test_impersonation_with_host_events_can_patch_legacy_profile(
    client: TestClient,
    db_session: Session,
    assign_role,
) -> None:
    """Admins impersonating with host_events scope can save Legacy studio."""
    from tests.helpers.auth import register_json

    _make_host(db_session, email="legacy-imp-host@example.com", slug="legacy-imp-host")
    host_headers = _login(client, "legacy-imp-host@example.com")
    host_id = client.get("/api/v1/auth/me", headers=host_headers).json()["id"]

    admin_reg = client.post(
        "/api/v1/auth/register",
        json=register_json(
            email="legacy-imp-admin@example.com",
            full_name="Legacy Imp Admin",
        ),
    )
    assert admin_reg.status_code == 201
    assign_role("legacy-imp-admin@example.com", "super_admin")
    admin_token = admin_reg.json()["access_token"]

    started = client.post(
        f"/api/v1/admin/users/{host_id}/impersonation/start",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reason": "legacy studio support", "duration_minutes": 30},
    )
    assert started.status_code == 200, started.text
    imp_token = started.json()["access_token"]

    res = client.patch(
        "/api/v1/host/legacy",
        headers={"Authorization": f"Bearer {imp_token}"},
        json={"display_name": "Impersonated Save", "tagline": "via admin"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["display_name"] == "Impersonated Save"
    assert res.json()["tagline"] == "via admin"


def test_host_cannot_update_another_host_legacy(
    client: TestClient, db_session: Session
) -> None:
    owner = _make_host(db_session, email="studio-owner@example.com", slug="studio-owner")
    other = _make_host(
        db_session, email="studio-other@example.com", slug="studio-other"
    )
    headers = _login(client, "studio-owner@example.com")

    blocks = client.get("/api/v1/host/legacy/content-blocks", headers=headers)
    assert blocks.status_code == 200
    for block in blocks.json():
        assert block["host_id"] == str(owner.id)
        assert block["host_id"] != str(other.id)

    # Patching as owner must not mutate the other host's page settings
    client.patch(
        "/api/v1/host/legacy",
        headers=headers,
        json={"tagline": "Owner only tagline"},
    )
    other_page = client.get(f"/api/v1/u/{other.slug}/legacy")
    assert other_page.status_code == 200
    assert other_page.json().get("tagline") != "Owner only tagline"


def test_public_legacy_only_returns_visible_blocks(
    client: TestClient, db_session: Session
) -> None:
    host = _make_host(db_session, email="studio-vis@example.com", slug="studio-vis")
    headers = _login(client, "studio-vis@example.com")
    ensure_legacy_page(db_session, host.id)
    db_session.commit()

    blocks = client.get("/api/v1/host/legacy/content-blocks", headers=headers).json()
    reviews_block = next(b for b in blocks if b["block_type"] == "verified_reviews")
    toggle = client.post(
        f"/api/v1/host/legacy/content-blocks/{reviews_block['id']}/toggle",
        headers=headers,
    )
    assert toggle.status_code == 200
    assert toggle.json()["is_visible"] is False

    public = client.get(f"/api/v1/u/{host.slug}/legacy")
    assert public.status_code == 200
    body = public.json()
    types = [b["block_type"] for b in body["content_blocks"]]
    assert "verified_reviews" not in types
    assert body["reviews_block_hidden"] is True
    assert body["trust_note"]
    assert body["reviews"] == []


def test_content_block_reorder_and_toggle(
    client: TestClient, db_session: Session
) -> None:
    host = _make_host(db_session, email="studio-ord@example.com", slug="studio-ord")
    headers = _login(client, "studio-ord@example.com")
    ensure_default_blocks(db_session, host.id)
    db_session.commit()

    blocks = client.get("/api/v1/host/legacy/content-blocks", headers=headers).json()
    reversed_ids = [b["id"] for b in reversed(blocks)]
    reordered = client.post(
        "/api/v1/host/legacy/content-blocks/reorder",
        headers=headers,
        json={"ordered_ids": reversed_ids},
    )
    assert reordered.status_code == 200, reordered.text
    assert [b["id"] for b in reordered.json()] == reversed_ids

    first = reordered.json()[0]
    toggled = client.post(
        f"/api/v1/host/legacy/content-blocks/{first['id']}/toggle",
        headers=headers,
    )
    assert toggled.status_code == 200
    assert toggled.json()["is_visible"] is not first["is_visible"]


def test_featured_item_and_vault_locked(
    client: TestClient, db_session: Session
) -> None:
    host = _make_host(db_session, email="studio-feat@example.com", slug="studio-feat")
    headers = _login(client, "studio-feat@example.com")

    category = db_session.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=5)
    event = Event(
        title="Feature Night",
        slug="feature-night-studio",
        description="Upcoming featured event for Legacy studio tests.",
        host_id=host.id,
        category_id=category.id if category else None,
        status="published",
        start_datetime=start,
        end_datetime=start + timedelta(hours=4),
        city="Lagos",
        banner_url="https://cdn.example.com/e.jpg",
        published_at=datetime.now(UTC),
    )
    db_session.add(event)
    db_session.flush()

    vault = VaultItem(
        host_id=host.id,
        title="Locked Drop",
        slug="locked-drop",
        content_type="drop",
        status="published",
        preview_text="Teaser only",
        body="SECRET BODY",
        cover_url="https://cdn.example.com/v.jpg",
        moderation_status="approved",
        published_at=datetime.now(UTC),
    )
    db_session.add(vault)
    db_session.flush()
    db_session.add(
        VaultAccessRule(
            vault_item_id=vault.id,
            access_type="ticket_holders",
            require_check_in=True,
        )
    )
    db_session.commit()

    feat_event = client.post(
        "/api/v1/host/legacy/featured-items",
        headers=headers,
        json={
            "item_type": "event",
            "item_id": str(event.id),
            "placement": "featured_upcoming_event",
        },
    )
    assert feat_event.status_code == 200, feat_event.text

    feat_vault = client.post(
        "/api/v1/host/legacy/featured-items",
        headers=headers,
        json={
            "item_type": "vault_item",
            "item_id": str(vault.id),
            "placement": "featured_vault_item",
        },
    )
    assert feat_vault.status_code == 200, feat_vault.text

    public = client.get(f"/api/v1/legacy/{host.slug}")
    assert public.status_code == 200
    body = public.json()
    assert body["upcoming_events"]
    assert body["upcoming_events"][0]["id"] == str(event.id)
    assert body["vault_preview"]
    card = body["vault_preview"][0]
    assert card["id"] == str(vault.id)
    assert card["locked"] is True
    assert card["has_access"] is False
    assert card.get("featured") is True
    assert "SECRET BODY" not in str(body)
    assert "body" not in card


def test_vault_preview_manual_source_and_layout(
    client: TestClient, db_session: Session
) -> None:
    host = _make_host(db_session, email="studio-vault-m@example.com", slug="studio-vault-m")
    headers = _login(client, "studio-vault-m@example.com")

    items = []
    for i, slug in enumerate(("drop-a", "drop-b", "drop-c")):
        vault = VaultItem(
            host_id=host.id,
            title=f"Drop {slug}",
            slug=slug,
            content_type="text_post",
            status="published",
            preview_text=f"Teaser {slug}",
            body=f"SECRET {slug}",
            cover_url=f"https://cdn.example.com/{slug}.jpg",
            moderation_status="approved",
            published_at=datetime.now(UTC),
        )
        db_session.add(vault)
        db_session.flush()
        db_session.add(
            VaultAccessRule(
                vault_item_id=vault.id,
                access_type="followers_only",
            )
        )
        items.append(vault)
    db_session.commit()

    blocks = client.get("/api/v1/host/legacy/content-blocks", headers=headers)
    assert blocks.status_code == 200
    vault_block = next(b for b in blocks.json() if b["block_type"] == "vault_preview")

    updated = client.patch(
        f"/api/v1/host/legacy/content-blocks/{vault_block['id']}",
        headers=headers,
        json={
            "title_override": "Members only",
            "description_override": "Unlock inside the Vault.",
            "source_type": "manual",
            "layout_style": "featured_spotlight",
            "item_limit": 2,
            "config": {
                "vault_item_ids": [str(items[2].id), str(items[0].id)],
            },
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["source_type"] == "manual"
    assert updated.json()["layout_style"] == "featured_spotlight"

    public = client.get(f"/api/v1/legacy/{host.slug}")
    assert public.status_code == 200
    body = public.json()
    preview = body["vault_preview"]
    assert len(preview) == 2
    assert [c["id"] for c in preview] == [str(items[2].id), str(items[0].id)]
    assert all(c["locked"] is True for c in preview)
    assert all(c["has_access"] is False for c in preview)
    assert all(c["share_path"].startswith(f"/u/{host.slug}/vault/") for c in preview)
    assert "SECRET" not in str(body)

    block_public = next(
        b for b in body["content_blocks"] if b["block_type"] == "vault_preview"
    )
    assert block_public["title_override"] == "Members only"
    assert block_public["description_override"] == "Unlock inside the Vault."
    assert block_public["layout_style"] == "featured_spotlight"


def test_default_blocks_exist_without_custom_config(
    client: TestClient, db_session: Session
) -> None:
    host = _make_host(db_session, email="studio-def@example.com", slug="studio-def")
    public = client.get(f"/api/v1/u/{host.slug}/legacy")
    assert public.status_code == 200
    blocks = public.json()["content_blocks"]
    assert len(blocks) >= 8
    types = {b["block_type"] for b in blocks}
    assert "about" in types
    assert "upcoming_events" in types
    assert "verified_reviews" in types
    assert "vault_preview" in types

    db_count = (
        db_session.query(HostLegacyContentBlock)
        .filter(HostLegacyContentBlock.host_id == host.id)
        .count()
    )
    assert db_count >= 8


def test_verified_reviews_remain_intact(
    client: TestClient, db_session: Session
) -> None:
    host = _make_host(db_session, email="studio-rev@example.com", slug="studio-rev")

    buyer = User(
        email="studio-buyer@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Buyer",
        is_active=True,
    )
    buyer_role = get_role_by_name(db_session, "buyer")
    assert buyer_role is not None
    buyer.roles.append(buyer_role)
    db_session.add(buyer)
    db_session.flush()

    category = db_session.query(EventCategory).first()
    start = datetime.now(UTC) - timedelta(days=2)
    event = Event(
        title="Reviewed Night",
        slug="reviewed-night-studio",
        description="Past event for verified review integrity.",
        host_id=host.id,
        category_id=category.id if category else None,
        status="completed",
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        city="Lagos",
        published_at=start - timedelta(days=1),
    )
    db_session.add(event)
    db_session.flush()
    tt = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
        price=Decimal("1000.00"),
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
    order = Order(
        reference="PDY-STUDIO-REV1",
        buyer_user_id=buyer.id,
        event_id=event.id,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("1000.00"),
        total_amount=Decimal("1000.00"),
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
        unit_price=Decimal("1000.00"),
        line_total=Decimal("1000.00"),
        ticket_type_name="GA",
    )
    db_session.add(item)
    db_session.flush()
    ticket = Ticket(
        public_code=new_public_ticket_code(),
        order_id=order.id,
        order_item_id=item.id,
        event_id=event.id,
        ticket_type_id=tt.id,
        buyer_user_id=buyer.id,
        status="checked_in",
        ticket_type_name="GA",
        holder_name=buyer.full_name,
        holder_email=buyer.email,
        checked_in_at=datetime.now(UTC),
    )
    db_session.add(ticket)
    db_session.flush()
    review = VerifiedReview(
        event_id=event.id,
        host_id=host.id,
        reviewer_user_id=buyer.id,
        ticket_id=ticket.id,
        rating=2,
        title="Rough night",
        body="Not what I expected but still verified.",
        status="visible",
    )
    db_session.add(review)
    db_session.commit()

    headers = _login(client, "studio-rev@example.com")
    feat = client.post(
        "/api/v1/host/legacy/featured-items",
        headers=headers,
        json={
            "item_type": "review",
            "item_id": str(review.id),
            "placement": "featured_review",
        },
    )
    assert feat.status_code == 200, feat.text

    public = client.get(f"/api/v1/u/{host.slug}/legacy")
    assert public.status_code == 200
    reviews = public.json()["reviews"]
    assert any(r["rating"] == 2 for r in reviews)
    assert db_session.get(VerifiedReview, review.id).status == "visible"
    assert (
        db_session.query(HostLegacyFeaturedItem)
        .filter(HostLegacyFeaturedItem.host_id == host.id)
        .count()
        >= 1
    )
