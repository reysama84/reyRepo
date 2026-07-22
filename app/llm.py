"""Extract structured incident fields from a natural-language message.

Two strategies:
  * A real LLM call against any OpenAI-compatible chat-completions endpoint
    (OpenAI, Groq, and Gemini all expose one).
  * A deterministic heuristic fallback used when no API key is configured or the
    provider is ``heuristic``. This keeps the bot (and the test suite) working
    without network access or credentials.
"""

from __future__ import annotations

import json
import re

import httpx

from .config import Settings
from .models import TicketDraft, normalize_priority

EXTRACTION_SYSTEM_PROMPT = (
    "You are an IT service desk assistant. Read the employee's message and extract "
    "incident fields. Respond with ONLY compact JSON using these keys: "
    "subject, description, category, priority, site, requester.\n"
    "- subject: short summary, max 100 chars\n"
    "- description: the full problem detail\n"
    "- category: one of Email, Hardware, Software, Network, Access, Other\n"
    "- priority: one of Low, Medium, High, Urgent (infer urgency from the wording)\n"
    "- site: office/location if mentioned, else null\n"
    "- requester: the person's name if mentioned, else null\n"
    "Use null for any field you cannot determine."
)

# Keyword -> category, checked in order.
_CATEGORY_KEYWORDS = [
    ("Email", ("email", "outlook", "mailbox", "inbox", "smtp", "exchange")),
    ("Network", ("network", "wifi", "wi-fi", "vpn", "internet", "connection", "lan")),
    ("Hardware", ("laptop", "monitor", "keyboard", "mouse", "printer", "hardware", "battery", "screen")),
    ("Access", ("password", "login", "access", "account", "permission", "locked", "reset")),
    ("Software", ("software", "install", "application", "app", "license", "update", "crash")),
]

_URGENT_WORDS = ("urgent", "asap", "immediately", "critical", "emergency", "down", "cannot work", "can't work")
_HIGH_WORDS = ("important", "blocked", "stuck", "not working", "broken", "failed")


class LLMExtractor:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def extract(self, text: str) -> TicketDraft:
        provider = self.settings.llm_provider.lower()
        if provider == "heuristic" or not self.settings.llm_api_key:
            return self._heuristic(text)
        try:
            return await self._via_llm(text)
        except Exception:
            # Never let an LLM outage stop a ticket from being created.
            return self._heuristic(text)

    # ---- real LLM path ----

    async def _via_llm(self, text: str) -> TicketDraft:
        url = f"{self.settings.resolved_llm_base_url()}/chat/completions"
        payload = {
            "model": self.settings.llm_model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.settings.llm_api_key}"}
        async with httpx.AsyncClient(timeout=self.settings.request_timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
        return self._draft_from_json(content, fallback_text=text)

    def _draft_from_json(self, content: str, fallback_text: str) -> TicketDraft:
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return self._heuristic(fallback_text)
        draft = TicketDraft(
            subject=_clean(data.get("subject")),
            description=_clean(data.get("description")) or fallback_text.strip(),
            category=_clean(data.get("category")),
            priority=normalize_priority(_clean(data.get("priority"))),
            site=_clean(data.get("site")),
            requester=_clean(data.get("requester")),
        )
        return draft

    # ---- heuristic path ----

    def _heuristic(self, text: str) -> TicketDraft:
        cleaned = (text or "").strip()
        if not cleaned:
            return TicketDraft()

        first_sentence = re.split(r"(?<=[.!?])\s+", cleaned)[0]
        subject = first_sentence[:100].strip()

        lower = cleaned.lower()
        category = next(
            (cat for cat, words in _CATEGORY_KEYWORDS if any(w in lower for w in words)),
            "Other",
        )

        if any(w in lower for w in _URGENT_WORDS):
            priority = "Urgent"
        elif any(w in lower for w in _HIGH_WORDS):
            priority = "High"
        else:
            priority = "Medium"

        return TicketDraft(
            subject=subject,
            description=cleaned,
            category=category,
            priority=priority,
        )


def _clean(value) -> str | None:
    """Coerce a model value to a trimmed string, treating null-ish text as None."""
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in ("null", "none", "n/a", "unknown"):
        return None
    return s
