"""Review analyzer tests with mocked LLM."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

from src.analysis.review_analyzer import ReviewAnalyzer
from src.db.models import Review, ReviewAnalysisCreate
from src.schemas.review_analysis import ReviewAnalysisOutput


def _sample_review() -> Review:
    return Review(
        id=uuid4(),
        source="playstore",
        text="Discover Weekly keeps recommending the same artists every week.",
        rating=2,
        review_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        metadata={},
        content_hash="abc123",
    )


def _sample_output() -> ReviewAnalysisOutput:
    return ReviewAnalysisOutput(
        sentiment="negative",
        primary_problem="Repetitive recommendations",
        recommendation_complaint=True,
        user_goal="Discover new artists",
        listening_behavior="Uses Discover Weekly weekly",
        user_segment="Music Explorer",
        discovery_challenge="Recommendations lack variety",
        confidence_score=0.88,
    )


@patch("src.analysis.review_analyzer.structured_completion")
def test_analyze_one_maps_to_review_analysis_create(mock_completion):
    mock_completion.return_value = _sample_output()
    review = _sample_review()

    mock_repo = MagicMock()
    mock_repo.get_by_review_id.return_value = None

    analyzer = ReviewAnalyzer(analysis_repo=mock_repo)
    result = analyzer.analyze_one(review)

    assert isinstance(result, ReviewAnalysisCreate)
    assert result.review_id == review.id
    assert result.sentiment == "negative"
    assert result.user_segment == "Music Explorer"
    assert result.recommendation_complaint is True


@patch("src.analysis.review_analyzer.structured_completion")
def test_analyze_and_store_inserts(mock_completion):
    mock_completion.return_value = _sample_output()
    review = _sample_review()

    mock_repo = MagicMock()
    mock_repo.get_by_review_id.return_value = None
    mock_repo.insert.return_value = MagicMock()

    analyzer = ReviewAnalyzer(analysis_repo=mock_repo)
    stored = analyzer.analyze_and_store(review)

    assert stored is not None
    mock_repo.insert.assert_called_once()


@patch("src.analysis.review_analyzer.structured_completion")
def test_analyze_batch_skips_existing(mock_completion):
    review = _sample_review()
    mock_repo = MagicMock()
    mock_repo.get_by_review_id.return_value = object()

    analyzer = ReviewAnalyzer(
        settings=MagicMock(analysis_batch_size=15, analysis_request_delay_seconds=0),
        analysis_repo=mock_repo,
    )
    result = analyzer.analyze_batch([review])

    assert result.skipped == 1
    assert result.analyzed == 0
    assert result.analyzed_review_ids == [review.id]
    mock_completion.assert_not_called()


@patch("src.analysis.review_analyzer.structured_completion")
def test_analyze_batch_stops_on_quota_exceeded(mock_completion):
    from src.llm.errors import LlmQuotaExceededError

    mock_completion.side_effect = LlmQuotaExceededError("429 quota exceeded")
    reviews = [_sample_review(), _sample_review()]

    mock_repo = MagicMock()
    mock_repo.get_by_review_id.return_value = None

    analyzer = ReviewAnalyzer(
        settings=MagicMock(analysis_batch_size=15, analysis_request_delay_seconds=0),
        analysis_repo=mock_repo,
    )
    result = analyzer.analyze_batch(reviews)

    assert result.quota_exceeded is True
    assert result.failed == 1
    assert mock_completion.call_count == 1
