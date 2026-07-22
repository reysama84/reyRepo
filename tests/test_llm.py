from app.config import Settings
from app.llm import LLMExtractor
from app.models import normalize_priority


async def test_heuristic_extracts_subject_and_description():
    extractor = LLMExtractor(Settings(llm_provider="heuristic"))
    draft = await extractor.extract("Outlook cannot connect. It started this morning.")
    assert draft.subject == "Outlook cannot connect."
    assert "started this morning" in draft.description
    assert draft.category == "Email"
    assert draft.priority in ("Low", "Medium", "High", "Urgent")


async def test_heuristic_flags_urgency():
    extractor = LLMExtractor(Settings(llm_provider="heuristic"))
    draft = await extractor.extract("URGENT: the whole network is down, we cannot work")
    assert draft.priority == "Urgent"
    assert draft.category == "Network"


async def test_heuristic_empty_message():
    extractor = LLMExtractor(Settings(llm_provider="heuristic"))
    draft = await extractor.extract("   ")
    assert draft.missing_required() == ["subject", "description"]


async def test_missing_api_key_falls_back_to_heuristic():
    # provider=openai but no key -> must not attempt a network call
    extractor = LLMExtractor(Settings(llm_provider="openai", llm_api_key=""))
    draft = await extractor.extract("Printer on 3rd floor is jammed")
    assert draft.subject
    assert draft.category == "Hardware"


def test_normalize_priority():
    assert normalize_priority("critical") == "Urgent"
    assert normalize_priority("normal") == "Medium"
    assert normalize_priority("P1") == "Urgent"
    assert normalize_priority("nonsense") is None
    assert normalize_priority(None) is None
