"""Domain models shared across the LLM, conversation, and ServiceDesk layers."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

# Fields the LLM/heuristic tries to fill.
TICKET_FIELDS = ("subject", "description", "category", "priority", "site", "requester")

# Without these two we cannot open a meaningful incident, so we ask for them.
REQUIRED_FIELDS = ("subject", "description")

VALID_PRIORITIES = ("Low", "Medium", "High", "Urgent")


def normalize_priority(value: Optional[str]) -> Optional[str]:
    """Map free-form priority text onto the four canonical levels."""
    if not value:
        return None
    v = value.strip().lower()
    if v in ("low", "minor", "trivial"):
        return "Low"
    if v in ("medium", "normal", "moderate"):
        return "Medium"
    if v in ("high", "important", "major"):
        return "High"
    if v in ("urgent", "critical", "emergency", "p1", "sev1"):
        return "Urgent"
    return None


class TicketDraft(BaseModel):
    """A partially- or fully-filled incident, accumulated across conversation turns."""

    subject: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    site: Optional[str] = None
    requester: Optional[str] = None

    def merge(self, other: "TicketDraft") -> "TicketDraft":
        """Return a new draft where non-empty fields from ``other`` win."""
        data = self.model_dump()
        for key, value in other.model_dump().items():
            if value:
                data[key] = value
        return TicketDraft(**data)

    def missing_required(self) -> list[str]:
        return [f for f in REQUIRED_FIELDS if not getattr(self, f)]

    def is_complete(self) -> bool:
        return not self.missing_required()


class IncidentResult(BaseModel):
    """What ServiceDesk Plus returns after creating a request."""

    request_id: str
    status: str = "Open"
    priority: Optional[str] = None
