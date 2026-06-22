"""Embedding generation for reviews."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from uuid import UUID

from app.config import Settings, get_settings
from src.db.models import Review
from src.db.repositories.embeddings_repo import EmbeddingsRepository
from src.llm.embedding_factory import create_embedding_provider

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingBatchResult:
    attempted: int = 0
    embedded: int = 0
    skipped: int = 0
    failed: int = 0
    failed_review_ids: list[UUID] = field(default_factory=list)
    embedded_review_ids: list[UUID] = field(default_factory=list)


class EmbeddingService:
    def __init__(
        self,
        settings: Settings | None = None,
        embeddings_repo: EmbeddingsRepository | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._embeddings_repo = embeddings_repo or EmbeddingsRepository()
        self._provider = create_embedding_provider(self._settings)

    @property
    def model_name(self) -> str:
        return self._provider.model_name

    def embed_one(self, review: Review) -> list[float]:
        vectors = self._provider.embed_texts([review.text])
        if not vectors:
            raise ValueError(f"No embedding returned for review {review.id}")
        return vectors[0]

    def embed_and_store(self, review: Review) -> bool:
        if self._embeddings_repo.get_by_review_id(review.id):
            logger.debug("Skipping existing embedding for review %s", review.id)
            return False

        vector = self.embed_one(review)
        self._embeddings_repo.upsert(review.id, vector, self.model_name)
        return True

    def _record_embedded(self, result: EmbeddingBatchResult, review: Review) -> None:
        result.embedded += 1
        result.embedded_review_ids.append(review.id)

    def embed_batch(self, reviews: list[Review]) -> EmbeddingBatchResult:
        result = EmbeddingBatchResult()
        batch_size = self._settings.analysis_batch_size

        pending = [review for review in reviews if not self._embeddings_repo.get_by_review_id(review.id)]
        already_embedded = [review for review in reviews if self._embeddings_repo.get_by_review_id(review.id)]
        result.skipped = len(already_embedded)
        result.embedded_review_ids.extend(review.id for review in already_embedded)
        result.attempted = len(pending)

        for index in range(0, len(pending), batch_size):
            batch = pending[index : index + batch_size]
            texts = [review.text for review in batch]
            try:
                vectors = self._provider.embed_texts(texts)
                if len(vectors) != len(batch):
                    raise ValueError("Embedding batch size mismatch")

                for review, vector in zip(batch, vectors, strict=True):
                    self._embeddings_repo.upsert(review.id, vector, self.model_name)
                    self._record_embedded(result, review)
            except Exception as exc:
                logger.error("Embedding batch failed: %s", exc)
                for review in batch:
                    try:
                        if self.embed_and_store(review):
                            self._record_embedded(result, review)
                    except Exception:
                        result.failed += 1
                        result.failed_review_ids.append(review.id)

            if index + batch_size < len(pending):
                time.sleep(0.5)

        return result
