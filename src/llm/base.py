"""LLM and embedding provider protocols."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel


class LLMProvider(Protocol):
    def structured_completion(
        self,
        system_prompt: str,
        user_content: str,
        schema_model: type[BaseModel],
    ) -> BaseModel:
        """Return a validated Pydantic model from a structured LLM response."""


class EmbeddingProvider(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return embedding vectors for a batch of texts."""

    @property
    def model_name(self) -> str:
        """Embedding model identifier stored with vectors."""

    @property
    def dimensions(self) -> int:
        """Vector dimensionality."""
