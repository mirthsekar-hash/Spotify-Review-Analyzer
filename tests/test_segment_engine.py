"""Segment engine tests with mocked LLM and repositories."""

from unittest.mock import MagicMock, patch

from src.analysis.segment_engine import SegmentEngine, compute_recommendation_trust_score
from src.db.repositories.analysis_repo import EXPECTED_USER_SEGMENTS, SegmentAggregate
from src.schemas.segments import SegmentationOutput


def _segmentation_output() -> SegmentationOutput:
    segments = []
    for segment_name in EXPECTED_USER_SEGMENTS:
        segments.append(
            {
                "segment_name": segment_name,
                "listening_goals": [f"{segment_name} goal"],
                "discovery_behavior": [f"{segment_name} behavior"],
                "top_frustrations": [f"{segment_name} frustration"],
                "narrative_summary": f"Summary for {segment_name}.",
            }
        )
    return SegmentationOutput.model_validate({"segments": segments})


def _aggregates() -> dict:
    return {
        segment: SegmentAggregate(
            segment_name=segment,
            size=10 if segment == "Music Explorer" else 5,
            top_user_goals=[f"{segment} goal"],
            top_listening_behaviors=[f"{segment} behavior"],
            top_discovery_challenges=[f"{segment} challenge"],
            top_primary_problems=[f"{segment} problem"],
            recommendation_complaint_rate=0.2 if segment == "Music Explorer" else 0.4,
            sentiment_counts={"negative": 3, "positive": 2},
        )
        for segment in EXPECTED_USER_SEGMENTS
    }


@patch("src.analysis.segment_engine.structured_completion")
def test_segment_engine_upserts_all_segments(mock_completion):
    mock_completion.return_value = _segmentation_output()

    mock_analysis_repo = MagicMock()
    mock_analysis_repo.get_collective_rows.return_value = [{}] * 60
    mock_analysis_repo.aggregate_by_segment.return_value = _aggregates()

    mock_segments_repo = MagicMock()

    engine = SegmentEngine(
        settings=MagicMock(collective_analysis_threshold=50),
        analysis_repo=mock_analysis_repo,
        segments_repo=mock_segments_repo,
    )
    result = engine.run()

    assert result.segments_written == 5
    assert result.segment_names == list(EXPECTED_USER_SEGMENTS)
    assert mock_segments_repo.upsert.call_count == 5

    trust_scores = [
        call.args[0].recommendation_trust_score
        for call in mock_segments_repo.upsert.call_args_list
    ]
    assert len(set(trust_scores)) > 1


def test_compute_recommendation_trust_score():
    assert compute_recommendation_trust_score(0.0) == 100.0
    assert compute_recommendation_trust_score(0.25) == 75.0
    assert compute_recommendation_trust_score(1.0) == 0.0


def test_segment_engine_raises_when_insufficient_reviews():
    mock_analysis_repo = MagicMock()
    mock_analysis_repo.get_collective_rows.return_value = [{}] * 10

    engine = SegmentEngine(
        settings=MagicMock(collective_analysis_threshold=50),
        analysis_repo=mock_analysis_repo,
        segments_repo=MagicMock(),
    )

    try:
        engine.run()
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "at least 50" in str(exc)
