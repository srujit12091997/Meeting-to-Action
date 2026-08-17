"""Central configuration, loaded from the .env file.

Everything reads settings from here so swapping MVP -> production
(e.g. SQLite -> Supabase Postgres) is a single change in one place.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM provider selector: "gemini" (free tier, default) or "anthropic"
    llm_provider: str = "gemini"

    # Google Gemini (free tier) — primary provider
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-lite-latest"

    # Claude / Anthropic — optional alternative provider
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-8"

    # Notion
    notion_api_key: str = ""
    notion_database_id: str = ""

    # Slack
    slack_bot_token: str = ""
    slack_default_channel: str = "#meeting-tasks"

    # Email (SMTP) — for sending the meeting summary
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""       # Gmail: use an App Password, not your login password
    email_from: str = ""          # defaults to smtp_user if blank

    # Database (SQLite for MVP, Postgres/Supabase URL for prod)
    database_url: str = "sqlite:///./meeting_agent.db"

    # Whisper / STT — base.en keeps up with live capture on CPU (~6x realtime).
    whisper_model: str = "base.en"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    # Observability (Langfuse)
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # App
    api_base_url: str = "http://localhost:8000"

    # Follow-up policy
    stale_after_days: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
