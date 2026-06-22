"""Theme extractor tests with mocked LLM and repositories."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from src.analysis.theme_extractor import ThemeExtractor, compute_impact_scores
from src.schemas.themes import ThemeExtractionOutput


def _collective_row(
    *,
    sentiment: str = "negative",
    source: str = "playstore",
    discovery_challenge: str = "Repetitive recommendations",
    primary_problem: str = "Stale playlists",
    recommendation_complaint: bool = True,
) -> dict:
    review_id = uuid4()
    return {
        "review_id": review_id,
        "source": source,
        "text": "Discover Weekly is the same every week.",
        "rating": 2,
        "sentiment": sentiment,
        "primary_problem": primary_problem,
        "recommendation_complaint": recommendation_complaint,
        "user_goal": "Find new music",
        "listening_behavior": "Uses Discover Weekly",
        "user_segment": "Music Explorer",
        "discovery_challenge": discovery_challenge,
    }


def _theme_output(review_ids: list) -> ThemeExtractionOutput:
    theme = {
        "theme_name": "Stale Discover Weekly",
        "frequency": 25,
        "representative_review_ids": review_ids[:3],
        "affected_segments": ["Music Explorer", "Casual Listener"],
        "summary": "Users report Discover Weekly feels repetitive.",
    }
    return ThemeExtractionOutput.model_validate({"themes": [theme] * 5})


@patch("src.analysis.theme_extractor.structured_completion")
def test_theme_extractor_persists_themes(mock_completion):
    rows = [_collective_row() for _ in range(60)]
    sample = rows[:50]
    review_ids = [row["review_id"] for row in sample]
    mock_completion.return_value = _theme_output(review_ids)

    mock_analysis_repo = MagicMock()
    mock_analysis_repo.get_collective_rows.return_value = rows
    mock_analysis_repo.top_field_frequencies.side_effect = [
        [("Repetitive recommendations", 30)],
        [("Stale playlists", 20)],
    ]
    mock_analysis_repo.sample_reviews_stratified.return_value = sample

    mock_themes_repo = MagicMock()
    stored_theme = MagicMock()
    stored_theme.id = uuid4()
    mock_themes_repo.upsert.return_value = stored_theme

    extractor = ThemeExtractor(
        settings=MagicMock(collective_analysis_threshold=50),
        analysis_repo=mock_analysis_repo,
        themes_repo=mock_themes_repo,
    )
    result = extractor.run()

    assert result.themes_written == 5
    assert result.analyzed_review_count == 60
    assert mock_themes_repo.upsert.call_count == 5
    assert mock_themes_repo.replace_theme_reviews.call_count == 5


def test_compute_impact_scores_normalizes_to_100():
    rid1, rid2, rid3 = uuid4(), uuid4(), uuid4()
    analysis_by_review = {
        rid1: {"sentiment": "negative", "recommendation_complaint": True},
        rid2: {"sentiment": "negative", "recommendation_complaint": True},
        rid3: {"sentiment": "positive", "recommendation_complaint": False},
    }
    themes = _theme_output([rid1, rid2, rid3]).themes

    scores = compute_impact_scores(themes, analysis_by_review)
    assert scores["Stale Discover Weekly"] == 100.0


def test_theme_extractor_raises_when_insufficient_reviews():
    mock_analysis_repo = MagicMock()
    mock_analysis_repo.get_collective_rows.return_value = [_collective_row() for _ in range(10)]

    extractor = ThemeExtractor(
        settings=MagicMock(collective_analysis_threshold=50),
        analysis_repo=mock_analysis_repo,
        themes_repo=MagicMock(),
    )

    try:
        extractor.run()
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "at least 50" in str(exc)
