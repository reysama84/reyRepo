import pytest

from app.bot import Bot
from app.models import IncidentResult, TicketDraft
from app.servicedesk import ServiceDeskError
from tests.conftest import FakeExtractor, FakeServiceDesk


async def test_complete_message_creates_ticket():
    sdp = FakeServiceDesk(IncidentResult(request_id="INC0003456", status="Open"))
    bot = Bot(FakeExtractor(TicketDraft(subject="Outlook down", description="cannot connect", priority="Medium")), sdp)

    reply = await bot.handle("telegram", "chat1", "Outlook cannot connect")

    assert "INC0003456" in reply
    assert "created successfully" in reply
    assert len(sdp.created) == 1


async def test_missing_fields_prompts_then_completes_next_turn():
    # Turn 1: extractor yields only a subject -> bot should ask for description.
    extractor = FakeExtractor()
    sdp = FakeServiceDesk()
    bot = Bot(extractor, sdp)

    # Force an incomplete first draft (subject only).
    extractor.draft = TicketDraft(subject="Printer jammed")
    reply1 = await bot.handle("telegram", "c1", "Printer jammed")
    assert "detail" in reply1.lower() or "?" in reply1
    assert len(sdp.created) == 0

    # Turn 2: user supplies description -> draft becomes complete via merge.
    extractor.draft = TicketDraft(description="3rd floor printer keeps jamming")
    reply2 = await bot.handle("telegram", "c1", "3rd floor printer keeps jamming")
    assert "INC0003456" in reply2
    created = sdp.created[0]
    assert created.subject == "Printer jammed"
    assert created.description == "3rd floor printer keeps jamming"


async def test_greeting_resets_and_welcomes():
    bot = Bot(FakeExtractor(), FakeServiceDesk())
    reply = await bot.handle("whatsapp", "u1", "hi")
    assert "IT support" in reply
    assert "ticket" in reply.lower()


async def test_servicedesk_error_keeps_draft_and_apologizes():
    sdp = FakeServiceDesk(error=ServiceDeskError("boom"))
    bot = Bot(FakeExtractor(TicketDraft(subject="s", description="d")), sdp)
    reply = await bot.handle("telegram", "c9", "something broke")
    assert "couldn't create" in reply.lower()
    # Draft retained so a retry doesn't lose context.
    assert bot.store.get("telegram:c9").subject == "s"


async def test_sessions_are_isolated_per_chat():
    extractor = FakeExtractor(TicketDraft(subject="only subject"))
    bot = Bot(extractor, FakeServiceDesk())
    await bot.handle("telegram", "a", "issue A")
    await bot.handle("telegram", "b", "issue B")
    assert bot.store.get("telegram:a").subject == "only subject"
    assert bot.store.get("telegram:b").subject == "only subject"
    # Different platform, same id -> different session.
    assert bot.store.get("whatsapp:a").subject is None


async def test_empty_message_guidance():
    bot = Bot(FakeExtractor(), FakeServiceDesk())
    reply = await bot.handle("telegram", "c", "   ")
    assert "describing your IT issue" in reply
