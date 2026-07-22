"""Environment-driven configuration. No secrets live in the repo."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- LLM ---
    llm_provider: str = "heuristic"  # openai | groq | gemini | heuristic
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = ""

    # --- ServiceDesk Plus ---
    sdp_base_url: str = ""
    sdp_api_path: str = "/api/v3/requests"
    sdp_auth_token: str = ""
    sdp_default_site: str = ""
    sdp_default_category: str = ""

    # --- Telegram ---
    telegram_bot_token: str = ""

    # --- WhatsApp (Meta Cloud API) ---
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = "verify-me"

    request_timeout: float = 30.0

    def resolved_llm_base_url(self) -> str:
        """Base URL for the OpenAI-compatible chat-completions call."""
        if self.llm_base_url:
            return self.llm_base_url.rstrip("/")
        return {
            "openai": "https://api.openai.com/v1",
            "groq": "https://api.groq.com/openai/v1",
            "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
        }.get(self.llm_provider, "https://api.openai.com/v1")


@lru_cache
def get_settings() -> Settings:
    return Settings()
