"""Blog block editor — document validation, security, legacy compatibility."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.blog.document.conversion import blank_document, convert_legacy_markdown, wrap_legacy_body
from app.blog.document.render import document_to_html, document_to_markdown
from app.blog.document.validation import DocumentValidationError, validate_document


def test_blank_document_valid():
    doc = blank_document()
    out = validate_document(doc)
    assert out["version"] == 1
    assert len(out["blocks"]) >= 1


def test_invalid_block_type_rejected():
    doc = blank_document()
    doc["blocks"][0]["type"] = "evil_component"
    with pytest.raises(DocumentValidationError):
        validate_document(doc)


def test_unsafe_url_rejected():
    doc = blank_document()
    doc["blocks"] = [
        {
            "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "type": "cta",
            "variant": "default",
            "props": {},
            "content": {"label": "Click", "href": "javascript:alert(1)"},
            "children": [],
        }
    ]
    with pytest.raises(DocumentValidationError):
        validate_document(doc)


def test_duplicate_block_id_rejected():
    doc = blank_document()
    bid = doc["blocks"][0]["id"]
    doc["blocks"].append({**doc["blocks"][0], "id": bid})
    with pytest.raises(DocumentValidationError):
        validate_document(doc)


def test_legacy_wrap_and_render():
    body = "## Hello\n\nSome **markdown** content."
    doc = wrap_legacy_body(body)
    html = document_to_html(doc)
    assert "blog-document" in html or "blog-prose" in html
    md = document_to_markdown(doc)
    assert "Hello" in md


def test_convert_legacy_markdown():
    body = "## Section one\n\nParagraph.\n\n## Section two\n\nMore text."
    doc = convert_legacy_markdown(body)
    assert len(doc["blocks"]) >= 2
    validated = validate_document(doc)
    assert validated["blocks"]


def test_unsafe_html_rejected_at_validation():
    doc = blank_document()
    doc["blocks"][0]["content"] = {
        "html": "<p>Safe</p><script>alert(1)</script>",
        "markdown": "",
    }
    with pytest.raises(DocumentValidationError):
        validate_document(doc)


def test_safe_html_renders():
    doc = blank_document()
    doc["blocks"][0]["content"] = {
        "html": "<p>Safe paragraph</p>",
        "markdown": "",
    }
    html = document_to_html(validate_document(doc))
    assert "Safe paragraph" in html
    assert "<script" not in html.lower()


def _register(client: TestClient, email: str) -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "full_name": "Doc Tester",
            "gender": "prefer_not_to_say",
        },
    )
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _admin(client: TestClient, db: Session, assign_role, email: str) -> dict[str, str]:
    headers = _register(client, email)
    assign_role(email, "super_admin")
    return headers


def test_document_api_crud(client: TestClient, db_session: Session, assign_role):
    headers = _admin(client, db_session, assign_role, "blog-doc-admin@example.com")
    create = client.post(
        "/api/v1/admin/blog/posts",
        headers=headers,
        json={"title": "Doc test post", "body": "## Hello\n\nWorld"},
    )
    assert create.status_code == 201, create.text
    post_id = create.json()["id"]

    get_doc = client.get(
        f"/api/v1/admin/blog/posts/{post_id}/document",
        headers=headers,
    )
    assert get_doc.status_code == 200
    assert get_doc.json()["has_legacy_body_only"] is True

    doc = convert_legacy_markdown("## Converted\n\nBody text.")
    patch = client.patch(
        f"/api/v1/admin/blog/posts/{post_id}/document",
        headers=headers,
        json={
            "content_document": doc,
            "expected_content_version": create.json()["content_version"],
            "editor_mode": "layout",
        },
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["editor_mode"] == "layout"
    assert patch.json()["content_document"] is not None

    validate = client.post(
        f"/api/v1/admin/blog/posts/{post_id}/document/validate",
        headers=headers,
        json={"content_document": doc},
    )
    assert validate.status_code == 200
    assert validate.json()["valid"] is True


def test_layout_templates_list(client: TestClient, db_session: Session, assign_role):
    headers = _admin(client, db_session, assign_role, "blog-tmpl-admin@example.com")
    res = client.get("/api/v1/admin/blog/layout-templates", headers=headers)
    assert res.status_code == 200
    templates = res.json()
    assert len(templates) >= 10
    slugs = {t["slug"] for t in templates}
    assert "how-to-guide" in slugs
    assert "blank" in slugs


def test_unauthorized_document_forbidden(client: TestClient):
    res = client.get(
        "/api/v1/admin/blog/posts/00000000-0000-0000-0000-000000000001/document",
    )
    assert res.status_code in (401, 403, 404)
