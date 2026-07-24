"""Admin-controlled platform notification system."""

from app.admin_notifications.orchestrator import dispatch_typed, send_notification
from app.admin_notifications.settings_service import ensure_default_settings

__all__ = ["dispatch_typed", "send_notification", "ensure_default_settings"]
