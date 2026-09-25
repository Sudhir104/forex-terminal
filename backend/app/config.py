from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


def _csv(value: str) -> list[str]:
    return [v.strip() for v in (value or "").split(",") if v.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- core ---
    database_url: str = "sqlite:///./forex.db"
    jwt_secret: str = "change-me-in-production"
    access_token_minutes: int = 60 * 24 * 7
    cors_origins: str = "http://localhost:3000"
    cron_token: str = ""  # protects POST /api/internal/tick
    enable_scheduler: bool = True
    demo_mode: bool = False

    # --- provider chains (first = primary, rest = fallbacks / additional sources) ---
    fx_providers: str = "twelvedata,frankfurter"
    macro_providers: str = "fred,ecb,boc,boe"
    news_providers: str = "rss"
    calendar_providers: str = "official"

    # --- keys ---
    twelvedata_api_key: str = ""
    twelvedata_daily_credits: int = 800
    fred_api_key: str = ""
    tradingeconomics_api_key: str = ""
    finnhub_api_key: str = ""

    # --- polling ---
    fx_active_interval: int = 60      # seconds while someone is looking at the dashboard
    fx_idle_interval: int = 900       # seconds otherwise
    news_interval: int = 600
    macro_fast_interval: int = 3600   # rates, yields, VIX
    macro_full_interval: int = 21600  # everything
    calendar_interval: int = 21600
    scores_interval: int = 300

    # --- alerts ---
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    alert_score_move: float = 0.5

    # --- AI ---
    llm_provider: str = "none"        # none | anthropic | groq
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # --- helpers ---
    @property
    def cors_list(self) -> list[str]:
        return _csv(self.cors_origins)

    @property
    def fx_chain(self) -> list[str]:
        return ["demo"] if self.demo_mode else _csv(self.fx_providers)

    @property
    def macro_chain(self) -> list[str]:
        return ["demo"] if self.demo_mode else _csv(self.macro_providers)

    @property
    def news_chain(self) -> list[str]:
        return ["demo"] if self.demo_mode else _csv(self.news_providers)

    @property
    def calendar_chain(self) -> list[str]:
        return ["demo"] if self.demo_mode else _csv(self.calendar_providers)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
