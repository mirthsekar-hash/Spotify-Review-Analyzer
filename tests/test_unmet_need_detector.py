"""Unmet need detector tests with mocked LLM and repositories."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from src.analysis.unmet_need_detector import UnmetNeedDetector, compute_opportunity_scores
from src.schemas.unmet_needs import UnmetNeedsOutput


def _gap_row() -> dict:
    return {
        "review_id": uuid4(),
        "user_goal": "Discover new artists",
        "discovery_challenge": "Repetitive recommendations",
        "user_segment": "Music Explorer",
        "sentiment": "negative",
        "text": "Same songs every week.",
    }


def _unmet_needs_output(review_ids: list) -> UnmetNeedsOutput:
    item = {
        "need": "Mood-aware discovery",
        "frequency": 18,
        "supporting_review_ids": review_ids[:2],
        "affected_segments": ["Casual Listener", "Music Explorer"],
        "severity_score": 0.8,
        "suggested_ai_solutions": ["Context-aware playlist generation"],
    }
    return UnmetNeedsOutput.model_validate({"unmet_needs": [item] * 5})


@patch("src.analysis.unmet_need_detector.structured_completion")
def test_unmet_need_detector_persists_needs(mock_completion):
    rows = [_gap_row() for _ in range(60)]
    review_ids = [row["review_id"] for row in rows]
    gaps = [("Discover new artists", "Repetitive recommendations", 60, rows)]
    mock_completion.return_value = _unmet_needs_output(review_ids)

    mock_analysis_repo = MagicMock()
    mock_analysis_repo.get_collective_rows.return_value = rows
    mock_analysis_repo.top_goal_challenge_gaps.return_value = gaps

    mock_unmet_needs_repo = MagicMock()

    detector = UnmetNeedDetector(
        settings=MagicMock(collective_analysis_threshold=50),
        analysis_repo=mock_analysis_repo,
        unmet_needs_repo=mock_unmet_needs_repo,
    )
    result = detector.run()

    assert result.needs_written == 5
    assert result.gap_pairs_used == 1
    assert mock_unmet_needs_repo.upsert.call_count == 5


def test_compute_opportunity_scores_normalizes_to_100():
    output = _unmet_needs_output([uuid4(), uuid4()])
    scores = compute_opportunity_scores(output.unmet_needs)
    assert scores["Mood-aware discovery"] == 100.0


def test_unmet_need_detector_requires_gap_pairs():
    mock_analysis_repo = MagicMock()
    mock_analysis_repo.get_collective_rows.return_value = [_gap_row() for _ in range(60)]
    mock_analysis_repo.top_goal_challenge_gaps.return_value = []

    detector = UnmetNeedDetector(
        settings=MagicMock(collective_analysis_threshold=50),
        analysis_repo=mock_analysis_repo,
        unmet_needs_repo=MagicMock(),
    )

    try:
        detector.run()
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "gap pairs" in str(exc)
