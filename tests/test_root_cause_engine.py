"""Root cause engine tests with mocked LLM and repositories."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from src.analysis.root_cause_engine import RootCauseEngine
from src.db.models import Theme
from src.schemas.root_causes import RootCauseOutput


def _negative_row() -> dict:
    return {
        "review_id": uuid4(),
        "source": "playstore",
        "text": "Recommendations never change.",
        "sentiment": "negative",
        "primary_problem": "Stale playlists",
        "discovery_challenge": "Repetitive recommendations",
        "user_segment": "Music Explorer",
    }


def _theme() -> Theme:
    return Theme(
        id=uuid4(),
        theme_name="Stale Discover Weekly",
        frequency=30,
        impact_score=85.0,
        representative_review_ids=[],
        affected_segments=["Music Explorer"],
    )


def _root_cause_output(review_ids: list) -> RootCauseOutput:
    item = {
        "root_cause": "Collaborative filtering reinforces past taste",
        "frequency": 20,
        "supporting_evidence_ids": review_ids[:1],
        "affected_segments": ["Music Explorer"],
        "causal_explanation": "Historical plays dominate the recommendation model.",
    }
    return RootCauseOutput.model_validate({"root_causes": [item] * 5})


@patch("src.analysis.root_cause_engine.structured_completion")
def test_root_cause_engine_persists_causes(mock_completion):
    rows = [_negative_row() for _ in range(60)]
    sample = rows[:40]
    review_ids = [row["review_id"] for row in sample]
    mock_completion.return_value = _root_cause_output(review_ids)

    mock_analysis_repo = MagicMock()
    mock_analysis_repo.get_collective_rows.return_value = rows
    mock_analysis_repo.sample_negative_reviews.return_value = sample

    mock_themes_repo = MagicMock()
    mock_themes_repo.get_all.return_value = [_theme()]

    mock_root_causes_repo = MagicMock()

    engine = RootCauseEngine(
        settings=MagicMock(collective_analysis_threshold=50),
        analysis_repo=mock_analysis_repo,
        themes_repo=mock_themes_repo,
        root_causes_repo=mock_root_causes_repo,
    )
    result = engine.run()

    assert result.root_causes_written == 5
    assert result.themes_used == 1
    assert mock_root_causes_repo.upsert.call_count == 5


def test_root_cause_engine_requires_themes():
    mock_analysis_repo = MagicMock()
    mock_analysis_repo.get_collective_rows.return_value = [_negative_row() for _ in range(60)]

    engine = RootCauseEngine(
        settings=MagicMock(collective_analysis_threshold=50),
        analysis_repo=mock_analysis_repo,
        themes_repo=MagicMock(get_all=MagicMock(return_value=[])),
        root_causes_repo=MagicMock(),
    )

    try:
        engine.run()
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "No themes found" in str(exc)
