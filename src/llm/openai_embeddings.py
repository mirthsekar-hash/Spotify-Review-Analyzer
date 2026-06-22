"""OpenAI embedding provider (optional swap via EMBEDDING_PROVIDER=openai)."""

from __future__ import annotations

from app.config import Settings


class OpenAIEmbeddingProvider:
    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key.strip():
            raise ValueError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")

        from openai import OpenAI

        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_embedding_model
        self._dimensions = settings.embedding_dimensions

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        response = self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in response.data]
