"""FastAPI webhook server.

Routes (discovered/defined here — this is the greenfield entry point):
  GET  /health              -> liveness probe
  POST /webhook/telegram    -> Telegram Bot API updates
  GET  /webhook/whatsapp    -> Meta Cloud API subscription verification
  POST /webhook/whatsapp    -> Meta Cloud API inbound messages
"""

from __future__ import annotations

from fastapi import FastAPI, Query, Request, Response

from . import __version__
from .bot import Bot
from .config import Settings, get_settings
from .conversation import SessionStore
from .llm import LLMExtractor
from .messaging import telegram, whatsapp
from .servicedesk import ServiceDeskClient


def build_bot(settings: Settings) -> Bot:
    return Bot(
        extractor=LLMExtractor(settings),
        sdp_client=ServiceDeskClient(settings),
        store=SessionStore(),
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="IT Support Ticket Bot", version=__version__)
    # One shared bot per process so conversation state persists across requests.
    app.state.settings = settings
    app.state.bot = build_bot(settings)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "version": __version__}

    @app.post("/webhook/telegram")
    async def telegram_webhook(request: Request) -> dict:
        update = await request.json()
        parsed = telegram.parse_update(update)
        if parsed is None:
            return {"ok": True, "skipped": True}
        chat_id, text = parsed
        reply = await app.state.bot.handle("telegram", chat_id, text)
        await telegram.send_message(app.state.settings, chat_id, reply)
        return {"ok": True}

    @app.get("/webhook/whatsapp")
    async def whatsapp_verify(
        hub_mode: str = Query("", alias="hub.mode"),
        hub_verify_token: str = Query("", alias="hub.verify_token"),
        hub_challenge: str = Query("", alias="hub.challenge"),
    ):
        challenge = whatsapp.verify_subscription(
            app.state.settings, hub_mode, hub_verify_token, hub_challenge
        )
        if challenge is None:
            return Response(status_code=403, content="verification failed")
        return Response(status_code=200, content=challenge, media_type="text/plain")

    @app.post("/webhook/whatsapp")
    async def whatsapp_webhook(request: Request) -> dict:
        payload = await request.json()
        parsed = whatsapp.parse_message(payload)
        if parsed is None:
            return {"ok": True, "skipped": True}
        from_number, text = parsed
        reply = await app.state.bot.handle("whatsapp", from_number, text)
        await whatsapp.send_message(app.state.settings, from_number, reply)
        return {"ok": True}

    return app


app = create_app()
