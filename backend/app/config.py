"""Application configuration loaded from environment variables."""
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Core ---
    app_name: str = "AI Chat Widget SaaS"
    environment: str = "production"
    debug: bool = False

    # --- Database ---
    database_url: str = "postgresql+psycopg2://chat:chat@postgres:5432/chatdb"

    # --- Public base URL (used for the embed snippet shown in the admin) ---
    # e.g. https://your-app.onrender.com. When empty, the admin falls back to
    # the current request's base URL.
    public_base_url: str = ""

    # Directory holding the widget assets (widget.js, demo.html) for the backend
    # to serve directly. Used on single-service deploys (e.g. Render) where
    # there is no separate Nginx. Empty disables it (Nginx serves them locally).
    widget_assets_dir: str = ""

    # --- OpenAI ---
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    # Maximum number of file-search results injected into the model context.
    file_search_max_results: int = 8

    # --- Admin panel ---
    admin_username: str = "admin"
    admin_password: str = "change-me-in-production"

    # --- Security ---
    # Comma separated list of origins allowed for the admin API. The public
    # /api/chat endpoint validates origins per-website instead.
    admin_allowed_origins: str = "*"
    rate_limit_chat: str = "30/minute"
    rate_limit_default: str = "120/minute"

    # Number of previous (user+assistant) turns to replay into the model.
    conversation_memory_turns: int = 10

    @field_validator("admin_allowed_origins")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @field_validator("database_url")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        # Managed providers (e.g. Render) hand out postgres:// or postgresql://
        # URLs without an explicit driver; pin psycopg2 for SQLAlchemy 2.x.
        v = v.strip()
        if v.startswith("postgres://"):
            v = "postgresql+psycopg2://" + v[len("postgres://"):]
        elif v.startswith("postgresql://"):
            v = "postgresql+psycopg2://" + v[len("postgresql://"):]
        return v

    @property
    def admin_origins_list(self) -> List[str]:
        if self.admin_allowed_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.admin_allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
