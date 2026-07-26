"""Memories frontend revalidate notify — auth + wiring."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.core.frontend_revalidate import notify_memories_frontend_revalidate
from app.memories.service import invalidate_memory_caches


def test_memories_notify_skipped_without_secret(monkeypatch):
    monkeypatch.setattr(
        "app.core.frontend_revalidate.get_settings",
        lambda: MagicMock(revalidate_secret="", frontend_url="https://padeya.com"),
    )
    assert notify_memories_frontend_revalidate(slug="demo-food-and-flow") is False


def test_memories_notify_posts_bearer_secret(monkeypatch):
    monkeypatch.setattr(
        "app.core.frontend_revalidate.get_settings",
        lambda: MagicMock(
            revalidate_secret="test-revalidate-secret",
            frontend_url="https://padeya.com",
        ),
    )
    mock_response = MagicMock(status_code=200, text="ok")
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.post.return_value = mock_response

    with patch("app.core.frontend_revalidate.httpx.Client", return_value=mock_client):
        assert (
            notify_memories_frontend_revalidate(slug="demo-food-and-flow") is True
        )

    mock_client.post.assert_called_once()
    args, kwargs = mock_client.post.call_args
    assert args[0] == "https://padeya.com/api/revalidate/memories"
    assert kwargs["headers"]["Authorization"] == "Bearer test-revalidate-secret"
    assert kwargs["json"]["slug"] == "demo-food-and-flow"


def test_invalidate_memory_caches_notifies_frontend(monkeypatch):
    called: dict = {}

    def fake_notify(*, slug=None):
        called["slug"] = slug
        return True

    monkeypatch.setattr(
        "app.core.frontend_revalidate.notify_memories_frontend_revalidate",
        fake_notify,
    )
    with patch("app.core.cache_invalidation.invalidate_event_caches"):
        event = MagicMock(slug="demo-food-and-flow", id="x", host_id="y")
        invalidate_memory_caches(event)
    assert called["slug"] == "demo-food-and-flow"
