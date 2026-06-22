"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Supabase
    supabase_url: str = ""
    supabase_service_key: str = ""

    # LLM provider
    llm_provider: Literal["gemini", "openai", "groq"] = "groq"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # Embeddings
    embedding_provider: Literal["gemini", "openai"] = "gemini"
    gemini_embedding_model: str = "gemini-embedding-001"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 768

    # Reddit
    reddit_user_agent: str = ""
    reddit_request_delay_seconds: int = 7

    # Store targets
    spotify_play_store_app_id: str = "com.spotify.music"
    spotify_app_store_app_id: str = "324684580"

    # Ingestion targets
    min_reviews_playstore: int = 500
    min_reviews_appstore: int = 300
    min_reviews_reddit: int = 200
    app_store_use_library: bool = False

    # Pipeline tuning
    analysis_batch_size: int = 15
    analysis_request_delay_seconds: float = 4.0
    collective_analysis_threshold: int = 50
    rag_min_confidence: float = 0.5
    rag_top_k: int = 15
    rag_min_similarity: float = 0.45

    @field_validator(
        "supabase_url",
        "supabase_service_key",
        "gemini_api_key",
        "openai_api_key",
        "groq_api_key",
        "reddit_user_agent",
        mode="before",
    )
    @classmethod
    def strip_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().strip('"').strip("'")
        return value

    @field_validator("llm_provider", "embedding_provider", mode="before")
    @classmethod
    def normalize_provider(cls, value: str) -> str:
        return str(value).strip().lower()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        def streamlit_settings_source() -> dict[str, Any]:
            from src.deploy.secrets import streamlit_secret_fields  # noqa: PLC0415

            return streamlit_secret_fields()

        return (
            init_settings,
            env_settings,
            dotenv_settings,
            streamlit_settings_source,
            file_secret_settings,
        )

    def missing_required(self) -> list[str]:
        """Return human-readable names of missing required configuration."""
        missing: list[str] = []

        if not self.supabase_url.strip():
            missing.append("SUPABASE_URL")
        if not self.supabase_service_key.strip():
            missing.append("SUPABASE_SERVICE_KEY")

        if self.llm_provider == "gemini" and not self.gemini_api_key.strip():
            missing.append("GEMINI_API_KEY")
        if self.llm_provider == "openai" and not self.openai_api_key.strip():
            missing.append("OPENAI_API_KEY")
        if self.llm_provider == "groq" and not self.groq_api_key.strip():
            missing.append("GROQ_API_KEY")

        if self.embedding_provider == "gemini" and not self.gemini_api_key.strip():
            if "GEMINI_API_KEY" not in missing:
                missing.append("GEMINI_API_KEY")
        if self.embedding_provider == "openai" and not self.openai_api_key.strip():
            if "OPENAI_API_KEY" not in missing:
                missing.append("OPENAI_API_KEY")

        if not self.reddit_user_agent.strip():
            missing.append("REDDIT_USER_AGENT")

        return missing

    def is_configured(self) -> bool:
        return len(self.missing_required()) == 0

    def active_llm_model(self) -> str:
        if self.llm_provider == "groq":
            return self.groq_model
        if self.llm_provider == "openai":
            return self.openai_model
        return self.gemini_model


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
