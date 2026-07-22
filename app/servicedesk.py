"""ManageEngine ServiceDesk Plus REST API (v3) client.

The v3 API takes an ``input_data`` form field whose value is a JSON document with
a top-level ``request`` object. Lookup fields (priority, category, site, requester)
are passed as ``{"name": "..."}``. The response nests the created request under
``request`` with an ``id`` and a ``status.name``.

Docs: https://www.manageengine.com/products/service-desk/sdpod-v3-api/
"""

from __future__ import annotations

import json

import httpx

from .config import Settings
from .models import IncidentResult, TicketDraft


class ServiceDeskError(RuntimeError):
    pass


class ServiceDeskClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def endpoint(self) -> str:
        base = self.settings.sdp_base_url.rstrip("/")
        path = self.settings.sdp_api_path
        if not path.startswith("/"):
            path = "/" + path
        return f"{base}{path}"

    def build_input_data(self, draft: TicketDraft) -> dict:
        """Map a TicketDraft onto the SDP v3 request payload."""
        request: dict = {
            "subject": draft.subject,
            "description": draft.description,
        }
        category = draft.category or self.settings.sdp_default_category
        site = draft.site or self.settings.sdp_default_site
        if category:
            request["category"] = {"name": category}
        if draft.priority:
            request["priority"] = {"name": draft.priority}
        if site:
            request["site"] = {"name": site}
        if draft.requester:
            request["requester"] = {"name": draft.requester}
        return {"request": request}

    async def create_incident(self, draft: TicketDraft) -> IncidentResult:
        if not self.settings.sdp_base_url:
            raise ServiceDeskError("SDP_BASE_URL is not configured")

        headers = {"Accept": "application/vnd.manageengine.sdp.v3+json"}
        if self.settings.sdp_auth_token:
            # On-prem uses authtoken; cloud OAuth uses a Bearer header. Send both
            # so the same client works against either deployment.
            headers["authtoken"] = self.settings.sdp_auth_token
            headers["Authorization"] = f"Bearer {self.settings.sdp_auth_token}"

        data = {"input_data": json.dumps(self.build_input_data(draft))}

        async with httpx.AsyncClient(timeout=self.settings.request_timeout) as client:
            resp = await client.post(self.endpoint, data=data, headers=headers)

        if resp.status_code >= 400:
            raise ServiceDeskError(
                f"ServiceDesk Plus returned {resp.status_code}: {resp.text[:500]}"
            )

        return self._parse_response(resp.json(), draft)

    @staticmethod
    def _parse_response(body: dict, draft: TicketDraft) -> IncidentResult:
        request = body.get("request", body) if isinstance(body, dict) else {}
        request_id = str(
            request.get("id")
            or request.get("request_id")
            or body.get("request_id")
            or ""
        )
        if not request_id:
            raise ServiceDeskError(f"Could not read request id from response: {body}")

        status = "Open"
        raw_status = request.get("status")
        if isinstance(raw_status, dict):
            status = raw_status.get("name") or status
        elif isinstance(raw_status, str):
            status = raw_status
        elif isinstance(body.get("status"), str):
            status = body["status"]

        return IncidentResult(request_id=request_id, status=status, priority=draft.priority)
