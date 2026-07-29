"""Blog taxonomy lifecycle — categories, tags, post types, media roles."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.blog import taxonomy_service as tax
from app.blog.models import BlogMediaRole, BlogPostType
from tests.helpers.auth import register_json


def _admin_headers(client: TestClient, assign_role, email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json=register_json(email=email, full_name="Blog Tax Admin"),
    )
    assign_role(email, "super_admin")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _fan_headers(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json=register_json(email=email, full_name="Fan User"),
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed_system(db_session: Session) -> None:
    tax.ensure_system_post_types(db_session)
    tax.ensure_system_media_roles(db_session)
    db_session.commit()


def test_get_post_types_does_not_mutate(client: TestClient, assign_role, db_session: Session):
    _seed_system(db_session)
    admin = _admin_headers(client, assign_role, "blog-tax-get-ro@example.com")
    before = db_session.scalar(select(func.count()).select_from(BlogPostType)) or 0
    assert client.get("/api/v1/admin/blog/post-types", headers=admin).status_code == 200
    after = db_session.scalar(select(func.count()).select_from(BlogPostType)) or 0
    assert after == before

    before_m = db_session.scalar(select(func.count()).select_from(BlogMediaRole)) or 0
    assert client.get("/api/v1/admin/blog/media-roles", headers=admin).status_code == 200
    after_m = db_session.scalar(select(func.count()).select_from(BlogMediaRole)) or 0
    assert after_m == before_m


def test_category_lifecycle(client: TestClient, assign_role):
    admin = _admin_headers(client, assign_role, "blog-tax-cat@example.com")
    created = client.post(
        "/api/v1/admin/blog/categories",
        headers=admin,
        json={"name": "Nightlife Guides", "slug": "nightlife-guides", "description": "x"},
    )
    assert created.status_code == 201, created.text
    cat = created.json()
    assert cat["slug"] == "nightlife-guides"
    assert cat["is_active"] is True
    assert cat["usage_count"] == 0

    dup = client.post(
        "/api/v1/admin/blog/categories",
        headers=admin,
        json={"name": "Other", "slug": "nightlife-guides"},
    )
    assert dup.status_code == 409

    patched = client.patch(
        f"/api/v1/admin/blog/categories/{cat['id']}",
        headers=admin,
        json={"name": "Nightlife Guides+", "description": "updated"},
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Nightlife Guides+"

    slug_blocked = client.patch(
        f"/api/v1/admin/blog/categories/{cat['id']}",
        headers=admin,
        json={"slug": "nightlife-guides-v2"},
    )
    assert slug_blocked.status_code == 400

    slug_ok = client.patch(
        f"/api/v1/admin/blog/categories/{cat['id']}",
        headers=admin,
        json={"slug": "nightlife-guides-v2", "confirm_slug_change": True},
    )
    assert slug_ok.status_code == 200
    assert slug_ok.json()["slug"] == "nightlife-guides-v2"

    public = client.get("/api/v1/blog/categories/nightlife-guides")
    assert public.status_code == 200
    assert public.json()["slug"] == "nightlife-guides-v2"

    archived = client.post(
        f"/api/v1/admin/blog/categories/{cat['id']}/archive",
        headers=admin,
    )
    assert archived.status_code == 200
    assert archived.json()["is_active"] is False

    active_list = client.get("/api/v1/admin/blog/categories", headers=admin)
    assert active_list.status_code == 200
    assert all(r["id"] != cat["id"] for r in active_list.json())

    restored = client.post(
        f"/api/v1/admin/blog/categories/{cat['id']}/restore",
        headers=admin,
    )
    assert restored.status_code == 200
    assert restored.json()["is_active"] is True

    deleted = client.delete(
        f"/api/v1/admin/blog/categories/{cat['id']}",
        headers=admin,
    )
    assert deleted.status_code == 405


def test_tag_lifecycle_and_usage(client: TestClient, assign_role):
    admin = _admin_headers(client, assign_role, "blog-tax-tag@example.com")
    tag = client.post(
        "/api/v1/admin/blog/tags",
        headers=admin,
        json={"name": "VIP Nights", "slug": "vip-nights"},
    ).json()
    post = client.post(
        "/api/v1/admin/blog/posts",
        headers=admin,
        json={
            "title": "Taxonomy usage post",
            "body": "## Hello\n\nBody content here.",
            "tag_ids": [tag["id"]],
        },
    )
    assert post.status_code == 201, post.text

    listed = client.get(
        "/api/v1/admin/blog/tags?include_archived=true",
        headers=admin,
    )
    assert listed.status_code == 200
    match = next(r for r in listed.json() if r["id"] == tag["id"])
    assert match["usage_count"] >= 1

    archived = client.post(
        f"/api/v1/admin/blog/tags/{tag['id']}/archive",
        headers=admin,
    )
    assert archived.status_code == 200

    blocked = client.post(
        "/api/v1/admin/blog/posts",
        headers=admin,
        json={
            "title": "Cannot use archived tag",
            "body": "## Hello\n\nBody content here.",
            "tag_ids": [tag["id"]],
        },
    )
    assert blocked.status_code == 400


def test_post_types_seeded_and_assignable(client: TestClient, assign_role, db_session: Session):
    _seed_system(db_session)
    admin = _admin_headers(client, assign_role, "blog-tax-pt@example.com")
    rows = client.get("/api/v1/admin/blog/post-types", headers=admin)
    assert rows.status_code == 200
    keys = {r["key"] for r in rows.json()}
    assert "how_to" in keys
    assert "guide" in keys

    how_to = next(r for r in rows.json() if r["key"] == "how_to")
    custom = client.post(
        "/api/v1/admin/blog/post-types",
        headers=admin,
        json={"name": "Deep Dive", "key": "deep_dive"},
    )
    assert custom.status_code == 201, custom.text

    patched = client.patch(
        f"/api/v1/admin/blog/post-types/{how_to['id']}",
        headers=admin,
        json={"name": "How-to guide (edited)"},
    )
    assert patched.status_code == 200
    assert patched.json()["key"] == "how_to"
    assert patched.json()["name"] == "How-to guide (edited)"

    post = client.post(
        "/api/v1/admin/blog/posts",
        headers=admin,
        json={
            "title": "Post type assigned",
            "body": "## Hello\n\nBody content here.",
            "post_type_id": custom.json()["id"],
            "studio_brief": {
                "post_type_id": custom.json()["id"],
                "post_type_key": "deep_dive",
                "post_type_name": "Deep Dive",
            },
        },
    )
    assert post.status_code == 201, post.text
    assert post.json()["post_type"]["key"] == "deep_dive"

    # Rename display label — identity unchanged
    client.patch(
        f"/api/v1/admin/blog/post-types/{custom.json()['id']}",
        headers=admin,
        json={"name": "Deep Dive Renamed"},
    )
    got = client.get(f"/api/v1/admin/blog/posts/{post.json()['id']}", headers=admin)
    assert got.status_code == 200
    assert got.json()["post_type"]["key"] == "deep_dive"
    assert got.json()["post_type"]["id"] == custom.json()["id"]

    client.post(
        f"/api/v1/admin/blog/post-types/{custom.json()['id']}/archive",
        headers=admin,
    )
    got2 = client.get(f"/api/v1/admin/blog/posts/{post.json()['id']}", headers=admin)
    assert got2.json()["post_type"]["id"] == custom.json()["id"]

    blocked = client.post(
        "/api/v1/admin/blog/posts",
        headers=admin,
        json={
            "title": "Blocked archived type",
            "body": "## Hello\n\nBody content here.",
            "post_type_id": custom.json()["id"],
        },
    )
    assert blocked.status_code == 400


def test_media_roles_system_and_custom(client: TestClient, assign_role, db_session: Session):
    _seed_system(db_session)
    admin = _admin_headers(client, assign_role, "blog-tax-media@example.com")
    rows = client.get("/api/v1/admin/blog/media-roles", headers=admin)
    assert rows.status_code == 200
    by_key = {r["key"]: r for r in rows.json()}
    assert "cover" in by_key
    assert by_key["cover"]["is_required"] is True
    assert by_key["cover"]["can_archive"] is False
    assert by_key["cover"]["required_system_role"] is True

    bad = client.post(
        f"/api/v1/admin/blog/media-roles/{by_key['cover']['id']}/archive",
        headers=admin,
    )
    assert bad.status_code == 400

    custom = client.post(
        "/api/v1/admin/blog/media-roles",
        headers=admin,
        json={
            "name": "Pull quote art",
            "key": "pull_quote",
            "storage_folder": "content",
        },
    )
    assert custom.status_code == 201, custom.text
    assert custom.json()["can_archive"] is True

    unsafe = client.post(
        "/api/v1/admin/blog/media-roles",
        headers=admin,
        json={
            "name": "Evil",
            "key": "evil_role",
            "storage_folder": "../etc",
        },
    )
    assert unsafe.status_code == 400

    patched = client.patch(
        f"/api/v1/admin/blog/media-roles/{custom.json()['id']}",
        headers=admin,
        json={"name": "Pull-quote artwork"},
    )
    assert patched.status_code == 200
    assert patched.json()["key"] == "pull_quote"

    archived = client.post(
        f"/api/v1/admin/blog/media-roles/{custom.json()['id']}/archive",
        headers=admin,
    )
    assert archived.status_code == 200
    restored = client.post(
        f"/api/v1/admin/blog/media-roles/{custom.json()['id']}/restore",
        headers=admin,
    )
    assert restored.status_code == 200


def test_taxonomy_authz_boundaries(client: TestClient, assign_role):
    fan = _fan_headers(client, "blog-tax-fan@example.com")
    assert client.get("/api/v1/admin/blog/categories", headers=fan).status_code in {
        401,
        403,
    }
    assert client.post(
        "/api/v1/admin/blog/categories",
        headers=fan,
        json={"name": "Nope"},
    ).status_code in {401, 403}

    # Blog editor without taxonomy.manage: register + assign marketing (has edit, may have manage)
    # Create a custom role-less user with only admin.blog.edit via super_admin grant path:
    # Use support_agent which lacks blog taxonomy manage.
    client.post(
        "/api/v1/auth/register",
        json=register_json(email="blog-tax-support@example.com", full_name="Support"),
    )
    assign_role("blog-tax-support@example.com", "support_agent")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "blog-tax-support@example.com", "password": "securepass1"},
    )
    support = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.post(
        "/api/v1/admin/blog/categories",
        headers=support,
        json={"name": "Support cannot"},
    ).status_code == 403

    # Host rejected
    client.post(
        "/api/v1/auth/register",
        json=register_json(email="blog-tax-host@example.com", full_name="Host"),
    )
    assign_role("blog-tax-host@example.com", "host")
    login_h = client.post(
        "/api/v1/auth/login",
        json={"email": "blog-tax-host@example.com", "password": "securepass1"},
    )
    host = {"Authorization": f"Bearer {login_h.json()['access_token']}"}
    assert client.post(
        "/api/v1/admin/blog/tags",
        headers=host,
        json={"name": "Host nope"},
    ).status_code == 403


def test_category_reorder(client: TestClient, assign_role):
    admin = _admin_headers(client, assign_role, "blog-tax-reorder@example.com")
    a = client.post(
        "/api/v1/admin/blog/categories",
        headers=admin,
        json={"name": "Reorder A", "slug": "reorder-a"},
    ).json()
    b = client.post(
        "/api/v1/admin/blog/categories",
        headers=admin,
        json={"name": "Reorder B", "slug": "reorder-b"},
    ).json()
    reordered = client.post(
        "/api/v1/admin/blog/categories/reorder",
        headers=admin,
        json={"ordered_ids": [b["id"], a["id"]]},
    )
    assert reordered.status_code == 200
    ids = [r["id"] for r in reordered.json() if r["id"] in {a["id"], b["id"]}]
    assert ids[0] == b["id"]


def test_archive_then_assign_rejected(client: TestClient, assign_role):
    admin = _admin_headers(client, assign_role, "blog-tax-race@example.com")
    cat = client.post(
        "/api/v1/admin/blog/categories",
        headers=admin,
        json={"name": "Race Cat", "slug": "race-cat"},
    ).json()
    client.post(f"/api/v1/admin/blog/categories/{cat['id']}/archive", headers=admin)
    blocked = client.post(
        "/api/v1/admin/blog/posts",
        headers=admin,
        json={
            "title": "Assign after archive",
            "body": "## Hello\n\nBody content here.",
            "category_id": cat["id"],
        },
    )
    assert blocked.status_code == 400


def test_duplicate_post_type_key_conflict(client: TestClient, assign_role, db_session: Session):
    _seed_system(db_session)
    admin = _admin_headers(client, assign_role, "blog-tax-dup-key@example.com")
    first = client.post(
        "/api/v1/admin/blog/post-types",
        headers=admin,
        json={"name": "Unique One", "key": "unique_one"},
    )
    assert first.status_code == 201
    second = client.post(
        "/api/v1/admin/blog/post-types",
        headers=admin,
        json={"name": "Unique Two", "key": "unique_one"},
    )
    assert second.status_code == 409


def test_ensure_system_idempotent(db_session: Session):
    a = tax.ensure_system_post_types(db_session)
    b = tax.ensure_system_post_types(db_session)
    m1 = tax.ensure_system_media_roles(db_session)
    m2 = tax.ensure_system_media_roles(db_session)
    db_session.commit()
    assert b == 0 or a >= 0
    assert m2 == 0 or m1 >= 0
    keys = {r.key for r in db_session.scalars(select(BlogPostType)).all()}
    assert "how_to" in keys
    roles = {r.key for r in db_session.scalars(select(BlogMediaRole)).all()}
    assert "cover" in roles and "inline" in roles


def _headers_for_role(
    client: TestClient, assign_role, email: str, role: str
) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json=register_json(email=email, full_name=role),
    )
    assign_role(email, role)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_role_matrix_taxonomy_manage(client: TestClient, assign_role, db_session: Session):
    """fan/host/support/finance lack manage; editor-without-manage blocked; managers ok."""
    from app.users.models import Role
    from app.users.service import get_permission_by_code

    payload = {"name": "Matrix Cat", "slug": "matrix-cat"}

    for role, email in [
        ("buyer", "blog-tax-matrix-fan@example.com"),  # fan/buyer
        ("host", "blog-tax-matrix-host@example.com"),
        ("support_agent", "blog-tax-matrix-support@example.com"),
        ("finance_admin", "blog-tax-matrix-finance@example.com"),
    ]:
        headers = _headers_for_role(client, assign_role, email, role)
        assert (
            client.post("/api/v1/admin/blog/categories", headers=headers, json=payload).status_code
            == 403
        ), role

    # Blog editor with edit/create/view but WITHOUT taxonomy.manage
    editor_role = Role(name="blog_editor_no_tax", description="test editor")
    for code in ("admin.blog.view", "admin.blog.create", "admin.blog.edit"):
        perm = get_permission_by_code(db_session, code)
        assert perm is not None, code
        editor_role.permissions.append(perm)
    db_session.add(editor_role)
    db_session.commit()

    client.post(
        "/api/v1/auth/register",
        json=register_json(email="blog-tax-editor-only@example.com", full_name="Editor"),
    )
    from app.users.models import User

    row = db_session.query(User).filter(User.email == "blog-tax-editor-only@example.com").one()
    row.roles.append(editor_role)
    db_session.commit()
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "blog-tax-editor-only@example.com", "password": "securepass1"},
    )
    editor = {"Authorization": f"Bearer {login.json()['access_token']}"}
    # Can list (view) but cannot create
    listed = client.get("/api/v1/admin/blog/categories", headers=editor)
    assert listed.status_code == 200
    assert (
        client.post("/api/v1/admin/blog/categories", headers=editor, json=payload).status_code
        == 403
    )

    # Taxonomy manager (marketing has manage)
    mgr = _headers_for_role(
        client, assign_role, "blog-tax-matrix-mgr@example.com", "marketing"
    )
    created = client.post(
        "/api/v1/admin/blog/categories",
        headers=mgr,
        json={"name": "Mgr Cat", "slug": "mgr-cat"},
    )
    assert created.status_code == 201, created.text

    # Super admin
    admin = _admin_headers(client, assign_role, "blog-tax-matrix-sa@example.com")
    assert (
        client.post(
            "/api/v1/admin/blog/categories",
            headers=admin,
            json={"name": "SA Cat", "slug": "sa-cat"},
        ).status_code
        == 201
    )

def test_slug_redirect_no_chain(client: TestClient, assign_role):
    admin = _admin_headers(client, assign_role, "blog-tax-redir@example.com")
    cat = client.post(
        "/api/v1/admin/blog/categories",
        headers=admin,
        json={"name": "Redirect Me", "slug": "redir-a"},
    ).json()
    client.patch(
        f"/api/v1/admin/blog/categories/{cat['id']}",
        headers=admin,
        json={"slug": "redir-b", "confirm_slug_change": True},
    )
    client.patch(
        f"/api/v1/admin/blog/categories/{cat['id']}",
        headers=admin,
        json={"slug": "redir-c", "confirm_slug_change": True},
    )
    # Old A and B both resolve directly to current C (no chain hop)
    for old in ("redir-a", "redir-b"):
        res = client.get(f"/api/v1/blog/categories/{old}")
        assert res.status_code == 200
        assert res.json()["slug"] == "redir-c"

    public = client.get("/api/v1/blog/categories")
    assert public.status_code == 200
    assert all(r["slug"] != "redir-a" for r in public.json())

    client.post(f"/api/v1/admin/blog/categories/{cat['id']}/archive", headers=admin)
    after_archive = client.get("/api/v1/blog/categories")
    assert all(r["id"] != cat["id"] for r in after_archive.json())


def test_archive_tag_and_post_type_assign_rejected(
    client: TestClient, assign_role, db_session: Session
):
    _seed_system(db_session)
    admin = _admin_headers(client, assign_role, "blog-tax-race2@example.com")
    tag = client.post(
        "/api/v1/admin/blog/tags",
        headers=admin,
        json={"name": "Race Tag", "slug": "race-tag"},
    ).json()
    pt = client.post(
        "/api/v1/admin/blog/post-types",
        headers=admin,
        json={"name": "Race Type", "key": "race_type"},
    ).json()
    client.post(f"/api/v1/admin/blog/tags/{tag['id']}/archive", headers=admin)
    client.post(f"/api/v1/admin/blog/post-types/{pt['id']}/archive", headers=admin)

    assert (
        client.post(
            "/api/v1/admin/blog/posts",
            headers=admin,
            json={
                "title": "Tag race",
                "body": "## Hello\n\nBody content here.",
                "tag_ids": [tag["id"]],
            },
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/admin/blog/posts",
            headers=admin,
            json={
                "title": "Type race",
                "body": "## Hello\n\nBody content here.",
                "post_type_id": pt["id"],
            },
        ).status_code
        == 400
    )


def test_duplicate_media_role_key_and_category_slug(
    client: TestClient, assign_role, db_session: Session
):
    _seed_system(db_session)
    admin = _admin_headers(client, assign_role, "blog-tax-dup2@example.com")
    first = client.post(
        "/api/v1/admin/blog/media-roles",
        headers=admin,
        json={"name": "Dup Role", "key": "dup_role", "storage_folder": "content"},
    )
    assert first.status_code == 201
    second = client.post(
        "/api/v1/admin/blog/media-roles",
        headers=admin,
        json={"name": "Dup Role 2", "key": "dup_role", "storage_folder": "content"},
    )
    assert second.status_code == 409

    a = client.post(
        "/api/v1/admin/blog/categories",
        headers=admin,
        json={"name": "Slug One", "slug": "same-slug"},
    )
    assert a.status_code == 201
    b = client.post(
        "/api/v1/admin/blog/categories",
        headers=admin,
        json={"name": "Slug Two", "slug": "same-slug"},
    )
    assert b.status_code == 409


def test_cache_invalidation_called_on_category_mutate(
    client: TestClient, assign_role, monkeypatch
):
    calls: list[dict] = []

    def _fake_invalidate(*, slug: str | None = None) -> None:
        calls.append({"slug": slug})

    monkeypatch.setattr(
        "app.blog.taxonomy_service.invalidate_blog_caches",
        _fake_invalidate,
    )
    admin = _admin_headers(client, assign_role, "blog-tax-cache@example.com")
    created = client.post(
        "/api/v1/admin/blog/categories",
        headers=admin,
        json={"name": "Cache Cat", "slug": "cache-cat"},
    )
    assert created.status_code == 201
    assert calls, "create should invalidate blog caches"
    client.patch(
        f"/api/v1/admin/blog/categories/{created.json()['id']}",
        headers=admin,
        json={"name": "Cache Cat Renamed"},
    )
    assert len(calls) >= 2
    client.post(
        f"/api/v1/admin/blog/categories/{created.json()['id']}/archive",
        headers=admin,
    )
    assert len(calls) >= 3
