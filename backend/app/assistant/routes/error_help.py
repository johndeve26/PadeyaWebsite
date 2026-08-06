"""UI error code help for the assistant."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorHelpEntry:
    code: str
    summary: str
    next_steps: tuple[str, ...] = ()
    related_route_key: str | None = None


ERROR_HELP: dict[str, ErrorHelpEntry] = {
    "EVENT_PUBLISH_MISSING_TICKET_TYPE": ErrorHelpEntry(
        code="EVENT_PUBLISH_MISSING_TICKET_TYPE",
        summary="This event cannot be published until at least one ticket type exists.",
        next_steps=(
            "Open the event in Host Studio.",
            "Add a ticket type (name, price, quantity).",
            "Save, then try Publish again from the UI.",
        ),
        related_route_key="host_events",
    ),
    "EVENT_PUBLISH_MISSING_START": ErrorHelpEntry(
        code="EVENT_PUBLISH_MISSING_START",
        summary="Publishing requires a start date and time.",
        next_steps=("Set start (and end) datetime on the event details tab.",),
        related_route_key="host_events",
    ),
    "CHECKOUT_PAYMENT_FAILED": ErrorHelpEntry(
        code="CHECKOUT_PAYMENT_FAILED",
        summary="The payment attempt did not complete. No ticket was issued.",
        next_steps=(
            "Retry checkout with a valid payment method.",
            "If money left your account but you have no ticket, contact Support.",
        ),
        related_route_key="support",
    ),
    "AUTH_REQUIRED": ErrorHelpEntry(
        code="AUTH_REQUIRED",
        summary="This action requires you to sign in.",
        next_steps=("Sign in, then retry the action.",),
        related_route_key="account",
    ),
    "FORBIDDEN": ErrorHelpEntry(
        code="FORBIDDEN",
        summary="You don't have permission for this action.",
        next_steps=(
            "Switch to the correct workspace/role if you have one.",
            "Contact Support if you believe this is a mistake.",
        ),
        related_route_key="support",
    ),
    "RATE_LIMITED": ErrorHelpEntry(
        code="RATE_LIMITED",
        summary="Too many requests — wait a moment and try again.",
        next_steps=("Pause briefly, then retry.",),
    ),
}


def get_error_help(code: str | None) -> ErrorHelpEntry | None:
    if not code:
        return None
    return ERROR_HELP.get(code.strip().upper())


def explain_ui_errors(codes: list[str] | None) -> list[ErrorHelpEntry]:
    out: list[ErrorHelpEntry] = []
    for code in codes or []:
        entry = get_error_help(code)
        if entry:
            out.append(entry)
    return out
