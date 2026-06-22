"""Embedding provider factory."""

from __future__ import annotations

from functools import lru_cache

from app.config import Settings, get_settings
from src.llm.base import EmbeddingProvider
from src.llm.gemini_embeddings import GeminiEmbeddingProvider
from src.llm.openai_embeddings import OpenAIEmbeddingProvider


def create_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    config = settings or get_settings()

    if config.embedding_provider == "openai":
        return OpenAIEmbeddingProvider(config)
    return GeminiEmbeddingProvider(config)


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    return create_embedding_provider(get_settings())
