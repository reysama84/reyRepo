"""Shared fixtures and test doubles."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.models import IncidentResult, TicketDraft


@pytest.fixture
def settings() -> Settings:
    # Heuristic extractor, no live SDP — hermetic by default.
    return Settings(llm_provider="heuristic", sdp_base_url="https://sdp.test/app/itdesk")


class FakeExtractor:
    """Returns a canned draft, or echoes a heuristic-ish subject/description."""

    def __init__(self, draft: TicketDraft | None = None):
        self.draft = draft
        self.calls: list[str] = []

    async def extract(self, text: str) -> TicketDraft:
        self.calls.append(text)
        if self.draft is not None:
            return self.draft
        return TicketDraft(subject=text[:80], description=text, priority="Medium")


class FakeServiceDesk:
    def __init__(self, result: IncidentResult | None = None, error: Exception | None = None):
        self.result = result or IncidentResult(request_id="INC0003456", status="Open")
        self.error = error
        self.created: list[TicketDraft] = []

    async def create_incident(self, draft: TicketDraft) -> IncidentResult:
        self.created.append(draft)
        if self.error:
            raise self.error
        return IncidentResult(
            request_id=self.result.request_id,
            status=self.result.status,
            priority=draft.priority,
        )
