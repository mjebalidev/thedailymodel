from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # LLM
    gemini_api_key: str = ""
    # Ordered fallback chain: smartest first, most-available last. Each call
    # tries these in order and moves on if one is unavailable / rate-limited.
    gemini_models: str = "gemini-flash-latest,gemini-flash-lite-latest"
    # Optional single-model override (prepended to the chain if set).
    gemini_model: str = ""
    use_mock_llm: bool = True

    # Pipeline
    lookback_hours: int = 48
    max_candidates: int = 40
    max_articles: int = 12
    enable_web_search: bool = True

    # Relevance filter ("noise elimination" agent)
    enable_relevance_filter: bool = True
    relevance_min_score: int = 50  # 0-100; candidates below this are dropped

    # Languages — first is the base (edition is written in it); the rest are
    # produced by the translation agent. Use ISO 639-1 codes.
    languages: str = "en,fr,de"
    enable_translation: bool = True

    # Trigger / scheduler
    trigger_secret: str = ""
    enable_scheduler: bool = False
    daily_cron_hour: int = 6
    daily_cron_minute: int = 0

    # Storage / server
    database_url: str = "sqlite:///./ai_news.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    # Editions older than this many days are purged after each run (0 = keep all).
    retention_days: int = 365

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def language_list(self) -> list[str]:
        return [lang.strip().lower() for lang in self.languages.split(",") if lang.strip()]

    @property
    def base_language(self) -> str:
        langs = self.language_list
        return langs[0] if langs else "en"

    @property
    def target_languages(self) -> list[str]:
        """Non-base languages that need translation."""
        return self.language_list[1:]

    @property
    def gemini_model_list(self) -> list[str]:
        """Ordered fallback chain, with the optional single override first."""
        models = [m.strip() for m in self.gemini_models.split(",") if m.strip()]
        override = self.gemini_model.strip()
        if override:
            models = [override] + [m for m in models if m != override]
        return models

    @property
    def llm_is_live(self) -> bool:
        """True when a real Gemini call should be attempted."""
        return bool(self.gemini_api_key) and not self.use_mock_llm


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
