"""Marketplace taxonomy image upload + visual settings tests."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.taxonomy.service import create_category, create_location
from app.taxonomy.schemas import CategoryCreate, LocationCreate
from app.users.models import User
from tests.helpers.auth import register_json


def _user(db_session: Session, email: str) -> User:
    return db_session.query(User).filter_by(email=email).one()


def _admin(client: TestClient, assign_role, email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json=register_json(email=email, full_name="Tax Img Admin"),
    )
    assign_role(email, "super_admin")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _png_bytes() -> bytes:
    # Minimal valid 1x1 PNG (CRC-correct; Pillow-verifiable)
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
        b"\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def test_category_image_upload_and_public_fields(
    client: TestClient, assign_role, db_session: Session
):
    admin = _admin(client, assign_role, "tax-img-cat@example.com")
    cat = create_category(
        db_session,
        user=_user(db_session, "tax-img-cat@example.com"),
        payload=CategoryCreate(name="Nightlife Img", slug="nightlife-img"),
    )

    res = client.post(
        f"/api/v1/taxonomy/admin/media/upload?kind=category&term_id={cat.id}&image_role=primary&alt=Night+crowd",
        headers=admin,
        files={"file": ("night.png", _png_bytes(), "image/png")},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["url"]
    upload_ref = body.get("key") or body["url"]
    assert "public-media" in upload_ref or "taxonomy" in upload_ref

    listed = client.get("/api/v1/taxonomy/categories")
    assert listed.status_code == 200
    match = next(r for r in listed.json() if r["slug"] == "nightlife-img")
    assert match["primary_image_url"]
    assert match["image_url"] == match["primary_image_url"]
    assert "key" not in match
    assert match["primary_image_alt"] == "Night crowd"


def test_non_image_kind_rejected(client: TestClient, assign_role, db_session: Session):
    admin = _admin(client, assign_role, "tax-img-badkind@example.com")
    user = _user(db_session, "tax-img-badkind@example.com")
    cat = create_category(
        db_session,
        user=user,
        payload=CategoryCreate(name="Bad Kind", slug="x-img-kind"),
    )
    res = client.post(
        f"/api/v1/taxonomy/admin/media/upload?kind=tag&term_id={cat.id}",
        headers=admin,
        files={"file": ("x.png", _png_bytes(), "image/png")},
    )
    assert res.status_code == 400


def test_svg_rejected(client: TestClient, assign_role, db_session: Session):
    admin = _admin(client, assign_role, "tax-img-svg@example.com")
    user = _user(db_session, "tax-img-svg@example.com")
    cat = create_category(
        db_session, user=user, payload=CategoryCreate(name="SVG Cat", slug="svg-cat")
    )
    svg = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"></svg>'
    res = client.post(
        f"/api/v1/taxonomy/admin/media/upload?kind=category&term_id={cat.id}",
        headers=admin,
        files={"file": ("evil.png", svg, "image/png")},
    )
    assert res.status_code == 400


def test_unauthorized_upload(client: TestClient, assign_role, db_session: Session):
    client.post(
        "/api/v1/auth/register",
        json=register_json(email="tax-img-fan@example.com", full_name="Fan"),
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "tax-img-fan@example.com", "password": "securepass1"},
    )
    fan = {"Authorization": f"Bearer {login.json()['access_token']}"}
    admin = _admin(client, assign_role, "tax-img-owner@example.com")
    user = _user(db_session, "tax-img-owner@example.com")
    cat = create_category(
        db_session, user=user, payload=CategoryCreate(name="Own", slug="own-img")
    )
    res = client.post(
        f"/api/v1/taxonomy/admin/media/upload?kind=category&term_id={cat.id}",
        headers=fan,
        files={"file": ("x.png", _png_bytes(), "image/png")},
    )
    assert res.status_code == 403


def test_remove_primary_restores_null(
    client: TestClient, assign_role, db_session: Session
):
    admin = _admin(client, assign_role, "tax-img-rm@example.com")
    user = _user(db_session, "tax-img-rm@example.com")
    cat = create_category(
        db_session, user=user, payload=CategoryCreate(name="Rm", slug="rm-img")
    )
    up = client.post(
        f"/api/v1/taxonomy/admin/media/upload?kind=category&term_id={cat.id}",
        headers=admin,
        files={"file": ("x.png", _png_bytes(), "image/png")},
    )
    assert up.status_code == 201
    cleared = client.patch(
        f"/api/v1/taxonomy/admin/categories/{cat.id}/visuals",
        headers=admin,
        json={"clear_primary": True},
    )
    assert cleared.status_code == 200
    assert cleared.json()["primary_image_url"] is None


def test_city_image_and_focal(
    client: TestClient, assign_role, db_session: Session
):
    admin = _admin(client, assign_role, "tax-img-city@example.com")
    user = _user(db_session, "tax-img-city@example.com")
    # Parent chain: country → state → city (image-capable kinds are city/state/area)
    country = create_location(
        db_session,
        user=user,
        payload=LocationCreate(kind="country", name="Nigeria Img", slug="nigeria-img"),
    )
    state = create_location(
        db_session,
        user=user,
        payload=LocationCreate(
            kind="state",
            name="Lagos State Img",
            slug="lagos-state-img",
            parent_id=country.id,
        ),
    )
    city = create_location(
        db_session,
        user=user,
        payload=LocationCreate(
            kind="city",
            name="Lagos Img",
            slug="lagos-img",
            parent_id=state.id,
        ),
    )
    up = client.post(
        f"/api/v1/taxonomy/admin/media/upload?kind=city&term_id={city.id}&image_role=primary",
        headers=admin,
        files={"file": ("city.png", _png_bytes(), "image/png")},
    )
    assert up.status_code == 201, up.text
    patched = client.patch(
        f"/api/v1/taxonomy/admin/locations/{city.id}/visuals",
        headers=admin,
        json={
            "primary_image_alt": "Lagos skyline",
            "primary_image_focal_x": 0.3,
            "primary_image_focal_y": 0.7,
        },
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["primary_image_focal_x"] == 0.3
    assert patched.json()["primary_image_alt"] == "Lagos skyline"

    bad_focal = client.patch(
        f"/api/v1/taxonomy/admin/locations/{city.id}/visuals",
        headers=admin,
        json={"primary_image_focal_x": 1.5},
    )
    assert bad_focal.status_code == 422


def test_external_url_rejected(client: TestClient, assign_role, db_session: Session):
    admin = _admin(client, assign_role, "tax-img-ext@example.com")
    user = _user(db_session, "tax-img-ext@example.com")
    cat = create_category(
        db_session, user=user, payload=CategoryCreate(name="Ext", slug="ext-img")
    )
    res = client.patch(
        f"/api/v1/taxonomy/admin/categories/{cat.id}/visuals",
        headers=admin,
        json={"primary_image_url": "https://evil.example/x.jpg"},
    )
    assert res.status_code == 400
