import json

import httpx
import pytest

from app.config import Settings
from app.models import TicketDraft
from app.servicedesk import ServiceDeskClient, ServiceDeskError


def _client() -> ServiceDeskClient:
    return ServiceDeskClient(
        Settings(
            sdp_base_url="https://sdp.test/app/itdesk",
            sdp_auth_token="tok123",
            sdp_default_site="Jakarta HQ",
        )
    )


def test_build_input_data_maps_lookup_fields():
    client = _client()
    draft = TicketDraft(
        subject="Outlook cannot connect",
        description="Since this morning",
        category="Email",
        priority="Medium",
        requester="John Doe",
    )
    payload = client.build_input_data(draft)["request"]
    assert payload["subject"] == "Outlook cannot connect"
    assert payload["category"] == {"name": "Email"}
    assert payload["priority"] == {"name": "Medium"}
    assert payload["requester"] == {"name": "John Doe"}
    # default site applied when draft has none
    assert payload["site"] == {"name": "Jakarta HQ"}


def test_endpoint_joins_base_and_path():
    assert _client().endpoint == "https://sdp.test/app/itdesk/api/v3/requests"


async def test_create_incident_parses_v3_response(monkeypatch):
    client = _client()
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = request.content.decode()
        captured["authtoken"] = request.headers.get("authtoken")
        return httpx.Response(
            200,
            json={
                "request": {"id": "INC0003456", "status": {"name": "Open"}},
                "response_status": {"status": "success"},
            },
        )

    transport = httpx.MockTransport(handler)
    _patch_async_client(monkeypatch, transport)

    result = await client.create_incident(
        TicketDraft(subject="s", description="d", priority="High")
    )
    assert result.request_id == "INC0003456"
    assert result.status == "Open"
    assert result.priority == "High"
    assert captured["authtoken"] == "tok123"
    # input_data is form-encoded JSON
    assert "input_data" in captured["body"]


async def test_create_incident_raises_on_error_status(monkeypatch):
    client = _client()
    transport = httpx.MockTransport(lambda req: httpx.Response(400, text="bad request"))
    _patch_async_client(monkeypatch, transport)
    with pytest.raises(ServiceDeskError):
        await client.create_incident(TicketDraft(subject="s", description="d"))


async def test_create_incident_requires_base_url():
    client = ServiceDeskClient(Settings(sdp_base_url=""))
    with pytest.raises(ServiceDeskError):
        await client.create_incident(TicketDraft(subject="s", description="d"))


def _patch_async_client(monkeypatch, transport):
    """Force httpx.AsyncClient to use a MockTransport regardless of kwargs."""
    original = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs.pop("timeout", None)
        return original(transport=transport, **{k: v for k, v in kwargs.items() if k != "transport"})

    monkeypatch.setattr(httpx, "AsyncClient", factory)
