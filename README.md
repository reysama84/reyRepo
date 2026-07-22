# IT Support Ticket Bot (WhatsApp / Telegram → ServiceDesk Plus)

An AI chatbot that lets employees open IT support tickets by chatting in WhatsApp
or Telegram. It reads a natural-language message, extracts the incident fields with
an LLM (with a rule-based fallback), applies simple business rules, and creates an
incident in **ManageEngine ServiceDesk Plus** via its REST API — then replies with
the ticket number.

```
Employee ──▶ WhatsApp / Telegram ──▶ Webhook (this server)
                                        │
                                        ▼
                       LLM extraction (OpenAI / Groq / Gemini)
                       intent + entity extraction, conversation
                                        │
                                        ▼
                       Business rules (required fields, priority)
                                        │
                                        ▼
                       ServiceDesk Plus REST API (v3)
                                        │
                                        ▼
                       Ticket number returned to the user
```

## Why this shape

- **Adapters are thin, the bot is testable.** `app/bot.py` takes an extractor and a
  ServiceDesk client and returns reply text. Platform code (`app/messaging/*`) only
  parses inbound payloads and sends outbound replies. The whole flow is unit-tested
  without any network.
- **Works with no keys.** `LLM_PROVIDER=heuristic` (the default) extracts fields with
  rules, so you can run and test the bot before wiring up an LLM or SDP. The real LLM
  path targets any OpenAI-compatible endpoint (OpenAI, Groq, and Gemini all provide one).
- **Multi-turn.** If a message lacks a subject or description, the bot asks for it and
  merges the answer on the next turn.

## Endpoints

Defined in `app/main.py` (this is a greenfield service — these are the entry points):

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/health` | Liveness probe |
| POST | `/webhook/telegram` | Telegram Bot API updates |
| GET  | `/webhook/whatsapp` | Meta Cloud API subscription verification |
| POST | `/webhook/whatsapp` | Meta Cloud API inbound messages |

The outbound ServiceDesk Plus call is `POST {SDP_BASE_URL}{SDP_API_PATH}` (default
`/api/v3/requests`), the documented ManageEngine v3 API — see `app/servicedesk.py`.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt      # or requirements-dev.txt for tests
cp .env.example .env                  # fill in tokens
uvicorn app.main:app --reload --port 8000
```

Point your Telegram / WhatsApp webhook at `https://<host>/webhook/telegram` and
`https://<host>/webhook/whatsapp`.

## Configuration

All config is environment-driven (see `.env.example`). Nothing secret is committed.
Key variables: `LLM_PROVIDER`, `LLM_API_KEY`, `SDP_BASE_URL`, `SDP_AUTH_TOKEN`,
`TELEGRAM_BOT_TOKEN`, `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`,
`WHATSAPP_VERIFY_TOKEN`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

25 tests cover extraction, priority normalization, draft merging, the ServiceDesk v3
payload/response, the conversation flow (including multi-turn and error handling), and
both webhooks (Telegram + WhatsApp verification and messages).

## Security note

Per the ticket's acceptance criterion ("user can be anyone to chat with the bot"),
there is **no allowlist** on who can message the bot — any sender who reaches the
webhook can open a ticket. For a real deployment you should still:

- Verify webhook authenticity (Telegram secret token header; WhatsApp `X-Hub-Signature-256`).
- Rate-limit per sender to prevent ticket spam.
- Scope the ServiceDesk Plus token to request-creation only.

These are noted here rather than implemented so the open-access acceptance criterion
is met without hiding the tradeoff.
