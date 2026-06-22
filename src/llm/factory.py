"""LLM provider factory."""

from __future__ import annotations

from functools import lru_cache

from app.config import Settings, get_settings
from src.llm.base import LLMProvider
from src.llm.gemini_provider import GeminiProvider
from src.llm.groq_provider import GroqProvider
from src.llm.openai_provider import OpenAIProvider


def create_llm_provider(settings: Settings | None = None) -> LLMProvider:
    config = settings or get_settings()

    if config.llm_provider == "openai":
        return OpenAIProvider(config)
    if config.llm_provider == "groq":
        return GroqProvider(config)
    return GeminiProvider(config)


@lru_cache
def get_llm_provider() -> LLMProvider:
    return create_llm_provider(get_settings())
