"""Core orchestration: message in -> reply out.

Deliberately decoupled from FastAPI and from the messaging platforms so it can be
unit-tested with fake extractors / ServiceDesk clients.
"""

from __future__ import annotations

from . import conversation
from .conversation import SessionStore
from .llm import LLMExtractor
from .models import TicketDraft
from .servicedesk import ServiceDeskClient, ServiceDeskError


class Bot:
    def __init__(
        self,
        extractor: LLMExtractor,
        sdp_client: ServiceDeskClient,
        store: SessionStore | None = None,
    ):
        self.extractor = extractor
        self.sdp_client = sdp_client
        self.store = store or SessionStore()

    async def handle(self, platform: str, chat_id: str, text: str) -> str:
        text = (text or "").strip()
        session_key = f"{platform}:{chat_id}"

        if not text:
            return "Send me a message describing your IT issue and I'll open a ticket."

        if text.lower() in ("/start", "hi", "hello", "help", "/help"):
            self.store.clear(session_key)
            return (
                "👋 Hi! I'm the IT support bot. Describe your issue "
                "(e.g. \"Outlook can't connect since this morning\") "
                "and I'll open a ticket for you."
            )

        extracted: TicketDraft = await self.extractor.extract(text)
        draft = self.store.get(session_key).merge(extracted)

        missing = draft.missing_required()
        if missing:
            self.store.set(session_key, draft)
            return conversation.prompt_for_missing(missing)

        try:
            result = await self.sdp_client.create_incident(draft)
        except ServiceDeskError:
            # Keep the draft so the user can retry without re-typing everything.
            self.store.set(session_key, draft)
            return conversation.format_error()

        self.store.clear(session_key)
        return conversation.format_success(result, draft)
