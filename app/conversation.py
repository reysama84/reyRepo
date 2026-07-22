"""Conversation state, business rules, and user-facing message formatting."""

from __future__ import annotations

from typing import Dict

from .models import IncidentResult, TicketDraft

_FIELD_PROMPTS = {
    "subject": "a short summary of the problem",
    "description": "a bit more detail about what's happening",
}


class SessionStore:
    """In-memory partial-draft storage keyed by ``platform:chat_id``.

    Swap for Redis/DB in production; the interface is intentionally tiny.
    """

    def __init__(self) -> None:
        self._drafts: Dict[str, TicketDraft] = {}

    def get(self, key: str) -> TicketDraft:
        return self._drafts.get(key, TicketDraft())

    def set(self, key: str, draft: TicketDraft) -> None:
        self._drafts[key] = draft

    def clear(self, key: str) -> None:
        self._drafts.pop(key, None)


def prompt_for_missing(missing: list[str]) -> str:
    parts = [_FIELD_PROMPTS.get(f, f) for f in missing]
    if len(parts) == 1:
        needed = parts[0]
    else:
        needed = ", ".join(parts[:-1]) + f" and {parts[-1]}"
    return (
        "I can log that as an IT ticket. Could you give me "
        f"{needed}? Just reply here and I'll take care of it."
    )


def format_success(result: IncidentResult, draft: TicketDraft) -> str:
    lines = [
        "✅ Your incident has been created successfully.",
        f"Ticket Number: {result.request_id}",
        f"Status: {result.status}",
    ]
    priority = result.priority or draft.priority
    if priority:
        lines.append(f"Priority: {priority}")
    lines.append("Our support team will contact you shortly.")
    return "\n".join(lines)


def format_error() -> str:
    return (
        "⚠️ Sorry, I couldn't create your ticket right now. "
        "Please try again in a moment, or contact the IT helpdesk directly."
    )
