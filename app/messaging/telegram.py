"""Telegram Bot API adapter."""

from __future__ import annotations

from typing import Optional, Tuple

import httpx

from ..config import Settings


def parse_update(update: dict) -> Optional[Tuple[str, str]]:
    """Return ``(chat_id, text)`` from a Telegram update, or None if not a text msg."""
    message = update.get("message") or update.get("edited_message")
    if not message:
        return None
    text = message.get("text")
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if text is None or chat_id is None:
        return None
    return str(chat_id), text


async def send_message(settings: Settings, chat_id: str, text: str) -> None:
    if not settings.telegram_bot_token:
        return
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        await client.post(url, json={"chat_id": chat_id, "text": text})
