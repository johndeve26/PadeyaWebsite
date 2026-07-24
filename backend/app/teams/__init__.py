"""Host team authorization (central permission checker)."""

from app.teams.permissions import (
    can_scan_merch_pickup,
    can_scan_ticket,
    get_team_membership,
    has_event_permission,
    has_event_staff_assignment,
    has_host_permission,
    is_host_owner,
    merch_scan_denial_reason,
    require_event_permission,
    require_host_permission,
    ticket_scan_denial_reason,
)
from app.teams.scan_audit import DeskScanAuditLog, write_desk_scan_audit

__all__ = [
    "is_host_owner",
    "get_team_membership",
    "has_host_permission",
    "has_event_permission",
    "has_event_staff_assignment",
    "can_scan_ticket",
    "can_scan_merch_pickup",
    "ticket_scan_denial_reason",
    "merch_scan_denial_reason",
    "require_host_permission",
    "require_event_permission",
    "DeskScanAuditLog",
    "write_desk_scan_audit",
]
