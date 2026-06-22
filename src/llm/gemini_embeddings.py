"""Google Gemini embedding provider."""

from __future__ import annotations

from app.config import Settings


class GeminiEmbeddingProvider:
    def __init__(self, settings: Settings) -> None:
        if not settings.gemini_api_key.strip():
            raise ValueError("GEMINI_API_KEY is required when EMBEDDING_PROVIDER=gemini")

        from google import genai

        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_embedding_model
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

        from google.genai import types

        response = self._client.models.embed_content(
            model=self._model,
            contents=texts,
            config=types.EmbedContentConfig(output_dimensionality=self._dimensions),
        )

        embeddings = response.embeddings or []
        return [list(item.values) for item in embeddings]
