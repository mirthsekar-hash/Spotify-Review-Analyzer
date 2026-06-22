"""Analysis pipeline unit tests."""

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

from src.analysis.analysis_pipeline import AnalysisPipeline
from src.analysis.embedding_service import EmbeddingBatchResult
from src.analysis.review_analyzer import ReviewAnalysisBatchResult
from src.db.models import Review


def _sample_review() -> Review:
    return Review(
        id=uuid4(),
        source="playstore",
        text="Recommendations feel stale and repetitive.",
        rating=2,
        review_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        metadata={},
        content_hash="hash123",
    )


def test_pipeline_marks_only_successfully_analyzed_reviews():
    review = _sample_review()
    failed_id = uuid4()

    reviews_repo = MagicMock()
    reviews_repo.get_unanalyzed.return_value = [review]

    analyzer = MagicMock()
    analyzer.analyze_batch.return_value = ReviewAnalysisBatchResult(
        attempted=1,
        analyzed=1,
        analyzed_review_ids=[review.id],
    )

    embedding_service = MagicMock()
    embedding_service.embed_batch.return_value = EmbeddingBatchResult(
        attempted=1,
        embedded=1,
        embedded_review_ids=[review.id],
    )

    pipeline = AnalysisPipeline(
        reviews_repo=reviews_repo,
        analyzer=analyzer,
        embedding_service=embedding_service,
    )
    result = pipeline.run(limit=10)

    assert result.marked_analyzed == 1
    reviews_repo.mark_analyzed.assert_called_once_with([review.id])
    embedding_service.embed_batch.assert_called_once()
    assert failed_id not in result.processed_review_ids
