from app.models import TicketDraft


def test_merge_prefers_non_empty_other():
    base = TicketDraft(subject="Old", description="desc", priority="Low")
    update = TicketDraft(subject="New", site="Jakarta HQ")
    merged = base.merge(update)
    assert merged.subject == "New"          # overwritten
    assert merged.description == "desc"      # preserved (update had none)
    assert merged.site == "Jakarta HQ"       # added
    assert merged.priority == "Low"          # preserved


def test_missing_required():
    assert TicketDraft().missing_required() == ["subject", "description"]
    assert TicketDraft(subject="x").missing_required() == ["description"]
    assert TicketDraft(subject="x", description="y").missing_required() == []
    assert TicketDraft(subject="x", description="y").is_complete()
