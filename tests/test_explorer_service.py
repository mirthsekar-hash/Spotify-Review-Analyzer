"""Explorer service unit tests."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from src.db.models import RootCause, Segment, Theme, UnmetNeed
from src.services.explorer_service import ExplorerService, compute_segment_counts


def test_compute_segment_counts_from_analysis_rows():
    review_id = uuid4()
    rows = [{"review_id": str(review_id), "user_segment": "Music Explorer"}]
    counts = compute_segment_counts([review_id], rows)
    assert counts == {"Music Explorer": 1}


@patch("src.services.explorer_service.check_connection", return_value=True)
def test_get_themes_sorts_by_impact(mock_check):
    theme_high = Theme(
        id=uuid4(),
        theme_name="High impact",
        frequency=10,
        impact_score=90.0,
        representative_review_ids=[],
        affected_segments=["Music Explorer"],
    )
    theme_low = Theme(
        id=uuid4(),
        theme_name="Low impact",
        frequency=20,
        impact_score=30.0,
        representative_review_ids=[],
        affected_segments=["Casual Listener"],
    )
    themes_repo = MagicMock()
    themes_repo.get_all.return_value = [theme_low, theme_high]

    data = ExplorerService(themes_repo=themes_repo).get_themes()
    assert data.themes[0].theme_name == "High impact"
    assert data.db_connected is True


@patch("src.services.explorer_service.check_connection", return_value=True)
def test_get_theme_detail_links_related_by_segment(mock_check):
    theme_id = uuid4()
    theme = Theme(
        id=theme_id,
        theme_name="Stale DW",
        frequency=8,
        impact_score=75.0,
        representative_review_ids=[uuid4()],
        affected_segments=["Music Explorer"],
    )
    themes_repo = MagicMock()
    themes_repo.get_with_reviews.return_value = {
        "theme": theme,
        "reviews": [{"source": "playstore", "text": "Same songs", "rating": 2}],
        "review_ids": theme.representative_review_ids,
    }

    root_causes_repo = MagicMock()
    root_causes_repo.get_all.return_value = [
        RootCause(
            id=uuid4(),
            root_cause="Filter bubble",
            frequency=5,
            supporting_evidence_ids=[uuid4()],
            affected_segments=["Music Explorer"],
        )
    ]
    unmet_needs_repo = MagicMock()
    unmet_needs_repo.get_all.return_value = [
        UnmetNeed(
            id=uuid4(),
            need="Guided exploration",
            frequency=4,
            opportunity_score=80.0,
            supporting_review_ids=[uuid4(), uuid4()],
            suggested_ai_solutions=["Discovery coach"],
        )
    ]
    analysis_repo = MagicMock()
    analysis_repo.get_fields_by_review_ids.return_value = [
        {"review_id": str(theme.representative_review_ids[0]), "user_segment": "Music Explorer"}
    ]

    detail = ExplorerService(
        themes_repo=themes_repo,
        root_causes_repo=root_causes_repo,
        unmet_needs_repo=unmet_needs_repo,
        analysis_repo=analysis_repo,
    ).get_theme_detail(theme_id)

    assert detail.theme is not None
    assert len(detail.reviews) == 1
    assert detail.related_root_causes[0].root_cause == "Filter bubble"
    assert detail.related_unmet_needs[0].need == "Guided exploration"


@patch("src.services.explorer_service.check_connection", return_value=True)
def test_get_segments_returns_all(mock_check):
    segments_repo = MagicMock()
    segments_repo.get_all.return_value = [
        Segment(
            id=uuid4(),
            segment_name="Music Explorer",
            size=12,
            listening_goals=["Find new artists"],
            discovery_behavior=["Uses Discover Weekly"],
            top_frustrations=["Repetition"],
            recommendation_trust_score=72.5,
        )
    ]

    data = ExplorerService(segments_repo=segments_repo).get_segments()
    assert len(data.segments) == 1
    assert data.segments[0].segment_name == "Music Explorer"
