"""Fan Passport frontend revalidate notify — auth + wiring."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.core.cache_invalidation import invalidate_fan_public_caches
from app.core.frontend_revalidate import notify_fan_frontend_revalidate


def test_notify_skipped_without_secret(monkeypatch):
    monkeypatch.setattr(
        "app.core.frontend_revalidate.get_settings",
        lambda: MagicMock(revalidate_secret="", frontend_url="https://padeya.com"),
    )
    assert notify_fan_frontend_revalidate(username="alice") is False


def test_notify_posts_bearer_secret(monkeypatch):
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
            notify_fan_frontend_revalidate(
                username="alice", previous_username="old_alice"
            )
            is True
        )

    mock_client.post.assert_called_once()
    args, kwargs = mock_client.post.call_args
    assert args[0] == "https://padeya.com/api/revalidate/fan"
    assert kwargs["headers"]["Authorization"] == "Bearer test-revalidate-secret"
    assert kwargs["json"]["username"] == "alice"
    assert kwargs["json"]["previous_username"] == "old_alice"


def test_invalidate_fan_public_caches_calls_frontend_notify(monkeypatch):
    called: dict = {}

    def fake_notify(*, username=None, previous_username=None):
        called["username"] = username
        called["previous_username"] = previous_username
        return True

    monkeypatch.setattr(
        "app.core.frontend_revalidate.notify_fan_frontend_revalidate",
        fake_notify,
    )
    with patch("app.core.cache_invalidation.cache_delete_pattern"), patch(
        "app.core.cache_invalidation.cache_delete"
    ):
        invalidate_fan_public_caches(username="bob", previous_username="robert")
    assert called["username"] == "bob"
    assert called["previous_username"] == "robert"
