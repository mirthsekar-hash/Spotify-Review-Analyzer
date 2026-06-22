"""End-to-end per-review analysis and embedding pipeline."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from uuid import UUID

from app.config import Settings, get_settings
from src.analysis.embedding_service import EmbeddingBatchResult, EmbeddingService
from src.analysis.review_analyzer import ReviewAnalysisBatchResult, ReviewAnalyzer
from src.db.models import Review
from src.db.repositories.reviews_repo import ReviewsRepository

logger = logging.getLogger(__name__)


@dataclass
class AnalysisPipelineResult:
    reviews_fetched: int = 0
    analysis: ReviewAnalysisBatchResult = field(default_factory=ReviewAnalysisBatchResult)
    embeddings: EmbeddingBatchResult = field(default_factory=EmbeddingBatchResult)
    marked_analyzed: int = 0
    processed_review_ids: list[UUID] = field(default_factory=list)


class AnalysisPipeline:
    def __init__(
        self,
        settings: Settings | None = None,
        reviews_repo: ReviewsRepository | None = None,
        analyzer: ReviewAnalyzer | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._reviews_repo = reviews_repo or ReviewsRepository()
        self._analyzer = analyzer or ReviewAnalyzer(self._settings)
        self._embedding_service = embedding_service or EmbeddingService(self._settings)

    def run(self, limit: int | None = None) -> AnalysisPipelineResult:
        batch_limit = limit or self._settings.analysis_batch_size * 10
        unanalyzed = self._reviews_repo.get_unanalyzed(limit=batch_limit)
        return self._run_on_reviews(unanalyzed)

    def run_for_review_ids(self, review_ids: list[UUID]) -> AnalysisPipelineResult:
        if not review_ids:
            logger.info("No review IDs provided for analysis")
            return AnalysisPipelineResult()

        reviews = self._reviews_repo.get_by_ids(review_ids)
        unanalyzed = [review for review in reviews if review.analyzed_at is None]
        return self._run_on_reviews(unanalyzed)

    def _run_on_reviews(self, unanalyzed: list[Review]) -> AnalysisPipelineResult:
        result = AnalysisPipelineResult(reviews_fetched=len(unanalyzed))
        if not unanalyzed:
            logger.info("No unanalyzed reviews found")
            return result

        analysis_result = self._analyzer.analyze_batch(unanalyzed)
        result.analysis = analysis_result

        analyzed_reviews = [
            review for review in unanalyzed if review.id in analysis_result.analyzed_review_ids
        ]

        embedding_result = self._embedding_service.embed_batch(analyzed_reviews)
        result.embeddings = embedding_result

        completed_ids = [
            review_id
            for review_id in analysis_result.analyzed_review_ids
            if review_id in embedding_result.embedded_review_ids
        ]
        if completed_ids:
            self._reviews_repo.mark_analyzed(completed_ids)
            result.marked_analyzed = len(completed_ids)
            result.processed_review_ids = completed_ids

        return result
