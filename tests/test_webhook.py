from fastapi.testclient import TestClient

from app.bot import Bot
from app.config import Settings
from app.main import create_app
from app.models import IncidentResult, TicketDraft
from tests.conftest import FakeExtractor, FakeServiceDesk


def _app_with_fake_bot(sdp=None, extractor=None):
    settings = Settings(llm_provider="heuristic", telegram_bot_token="", whatsapp_token="")
    app = create_app(settings)
    # Replace the wired bot with a hermetic one (no network on send/create).
    app.state.bot = Bot(
        extractor or FakeExtractor(TicketDraft(subject="Outlook down", description="cannot connect", priority="Medium")),
        sdp or FakeServiceDesk(IncidentResult(request_id="INC0009", status="Open")),
    )
    return app


def test_health():
    client = TestClient(create_app(Settings()))
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_telegram_webhook_creates_ticket():
    sdp = FakeServiceDesk(IncidentResult(request_id="INC0009", status="Open"))
    client = TestClient(_app_with_fake_bot(sdp=sdp))
    update = {"message": {"chat": {"id": 12345}, "text": "Outlook cannot connect"}}
    resp = client.post("/webhook/telegram", json=update)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert len(sdp.created) == 1


def test_telegram_webhook_ignores_non_text_update():
    client = TestClient(_app_with_fake_bot())
    resp = client.post("/webhook/telegram", json={"message": {"chat": {"id": 1}}})
    assert resp.status_code == 200
    assert resp.json().get("skipped") is True


def test_whatsapp_verification_handshake():
    settings = Settings(whatsapp_verify_token="secret123")
    client = TestClient(create_app(settings))
    resp = client.get(
        "/webhook/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": "secret123", "hub.challenge": "42"},
    )
    assert resp.status_code == 200
    assert resp.text == "42"


def test_whatsapp_verification_rejects_bad_token():
    settings = Settings(whatsapp_verify_token="secret123")
    client = TestClient(create_app(settings))
    resp = client.get(
        "/webhook/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "42"},
    )
    assert resp.status_code == 403


def test_whatsapp_webhook_creates_ticket():
    sdp = FakeServiceDesk(IncidentResult(request_id="INC0010", status="Open"))
    client = TestClient(_app_with_fake_bot(sdp=sdp))
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "628123456789",
                                    "type": "text",
                                    "text": {"body": "Outlook cannot connect"},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    resp = client.post("/webhook/whatsapp", json=payload)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert len(sdp.created) == 1


def test_whatsapp_webhook_ignores_status_callback():
    client = TestClient(_app_with_fake_bot())
    payload = {"entry": [{"changes": [{"value": {"statuses": [{"status": "delivered"}]}}]}]}
    resp = client.post("/webhook/whatsapp", json=payload)
    assert resp.status_code == 200
    assert resp.json().get("skipped") is True
