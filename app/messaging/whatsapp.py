"""WhatsApp adapter for the Meta (Facebook) Cloud API."""

from __future__ import annotations

from typing import Optional, Tuple

import httpx

from ..config import Settings


def parse_message(payload: dict) -> Optional[Tuple[str, str]]:
    """Return ``(from_number, text)`` from a Meta Cloud API webhook, else None.

    Ignores status callbacks (delivered/read receipts) which carry no message.
    """
    try:
        entry = payload["entry"][0]
        change = entry["changes"][0]
        value = change["value"]
        messages = value.get("messages")
        if not messages:
            return None
        message = messages[0]
        if message.get("type") != "text":
            return None
        from_number = message["from"]
        text = message["text"]["body"]
    except (KeyError, IndexError, TypeError):
        return None
    return str(from_number), text


def verify_subscription(settings: Settings, mode: str, token: str, challenge: str):
    """GET handshake used by Meta when you register the webhook."""
    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        return challenge
    return None


async def send_message(settings: Settings, to_number: str, text: str) -> None:
    if not settings.whatsapp_token or not settings.whatsapp_phone_number_id:
        return
    url = (
        f"https://graph.facebook.com/v21.0/"
        f"{settings.whatsapp_phone_number_id}/messages"
    )
    headers = {"Authorization": f"Bearer {settings.whatsapp_token}"}
    body = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text},
    }
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        await client.post(url, json=body, headers=headers)
