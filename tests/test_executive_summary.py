"""Executive AI summary schema and service tests."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.db.models import Segment, Theme
from src.schemas.executive_summary import ExecutiveSummaryOutput, format_executive_summary_markdown
from src.services.dashboard_service import (
    DashboardService,
    ExecutiveSummaryData,
    build_executive_summary_user_content,
    references_collective_data,
)


def test_executive_summary_output_schema():
    output = ExecutiveSummaryOutput.model_validate(
        {
            "summary": "Spotify users report repetitive recommendations across discovery surfaces.",
            "key_findings": [
                "Music Explorer segment faces stale Discover Weekly (theme: Stale Discover Weekly).",
                "Playlist-Dependent Listener segment reports shuffle repetition.",
            ],
            "top_opportunity": "Refresh discovery mixes weekly with explicit novelty controls.",
        }
    )
    assert len(output.key_findings) == 2


def test_executive_summary_requires_at_least_two_findings():
    with pytest.raises(ValidationError):
        ExecutiveSummaryOutput.model_validate(
            {
                "summary": "Summary",
                "key_findings": ["Only one"],
                "top_opportunity": "Opportunity",
            }
        )


def test_format_executive_summary_markdown():
    output = ExecutiveSummaryOutput.model_validate(
        {
            "summary": "Users struggle with discovery.",
            "key_findings": ["Finding one", "Finding two"],
            "top_opportunity": "Improve shuffle diversity",
        }
    )
    markdown = format_executive_summary_markdown(output)
    assert "### Key Findings" in markdown
    assert "### Top Opportunity" in markdown
    assert "- Finding one" in markdown


def test_references_collective_data_detects_theme_names():
    output = ExecutiveSummaryOutput.model_validate(
        {
            "summary": "Stale Discover Weekly affects explorers.",
            "key_findings": ["Theme Stale Discover Weekly is prominent.", "Another point"],
            "top_opportunity": "Refresh mixes",
        }
    )
    assert references_collective_data(
        output,
        {"Stale Discover Weekly"},
        {"Music Explorer"},
    )


def test_build_executive_summary_user_content_includes_theme_names():
    kpis = ExecutiveSummaryData(
        total_reviews=100,
        total_analyzed=80,
        top_discovery_challenge="Repetitive playlists",
        top_discovery_challenge_count=20,
        most_affected_segment="Music Explorer",
        segment_negative_rate=55.0,
        recommendation_trust_score=62.0,
        db_connected=True,
    )
    themes = [
        Theme(
            id=uuid4(),
            theme_name="Stale Discover Weekly",
            frequency=12,
            impact_score=80.0,
            affected_segments=["Music Explorer"],
        )
    ]
    segments = [
        Segment(
            id=uuid4(),
            segment_name="Music Explorer",
            size=20,
            top_frustrations=["Same songs every week"],
        )
    ]
    content = build_executive_summary_user_content(kpis, themes, segments, [], [])
    assert "Stale Discover Weekly" in content
    assert "Music Explorer" in content
    assert "Repetitive playlists" in content


@patch("src.services.dashboard_service.structured_completion")
@patch("src.services.dashboard_service.check_connection", return_value=True)
def test_generate_executive_summary_returns_validated_output(mock_check, mock_completion):
    theme = Theme(
        id=uuid4(),
        theme_name="Shuffle Repetition",
        frequency=10,
        impact_score=70.0,
        affected_segments=["Playlist-Dependent Listener"],
    )
    segment = Segment(
        id=uuid4(),
        segment_name="Playlist-Dependent Listener",
        size=15,
        top_frustrations=["Same tracks on shuffle"],
    )
    mock_completion.return_value = ExecutiveSummaryOutput.model_validate(
        {
            "summary": "Playlist-Dependent Listener users report shuffle repetition (Shuffle Repetition).",
            "key_findings": [
                "Shuffle Repetition theme affects Playlist-Dependent Listener segment.",
                "Recommendation trust remains under pressure.",
            ],
            "top_opportunity": "Increase shuffle pool diversity",
        }
    )

    reviews_repo = MagicMock()
    reviews_repo.count_total.return_value = 50
    reviews_repo.count_analyzed.return_value = 50

    analysis_repo = MagicMock()
    analysis_repo.get_dashboard_fields.return_value = [
        {
            "discovery_challenge": "Repetitive playlists",
            "user_segment": "Playlist-Dependent Listener",
            "sentiment": "negative",
            "recommendation_complaint": True,
        }
    ]

    themes_repo = MagicMock()
    themes_repo.get_all.return_value = [theme]
    segments_repo = MagicMock()
    segments_repo.get_all.return_value = [segment]
    root_causes_repo = MagicMock()
    root_causes_repo.get_all.return_value = []
    unmet_needs_repo = MagicMock()
    unmet_needs_repo.get_all.return_value = []

    pipeline_repo = MagicMock()
    pipeline_repo.get_latest.return_value = None

    service = DashboardService(
        reviews_repo=reviews_repo,
        analysis_repo=analysis_repo,
        pipeline_runs_repo=pipeline_repo,
        themes_repo=themes_repo,
        segments_repo=segments_repo,
        root_causes_repo=root_causes_repo,
        unmet_needs_repo=unmet_needs_repo,
    )
    result = service.generate_executive_summary()

    assert result is not None
    assert result.available is True
    assert result.output is not None
    assert "Shuffle Repetition" in result.output.summary
    mock_completion.assert_called_once()


@patch("src.services.dashboard_service.check_connection", return_value=True)
def test_generate_executive_summary_unavailable_without_collective_data(mock_check):
    reviews_repo = MagicMock()
    reviews_repo.count_total.return_value = 50
    reviews_repo.count_analyzed.return_value = 50

    analysis_repo = MagicMock()
    analysis_repo.get_dashboard_fields.return_value = [
        {"discovery_challenge": "Test", "user_segment": "Music Explorer", "sentiment": "negative"}
    ]

    service = DashboardService(
        reviews_repo=reviews_repo,
        analysis_repo=analysis_repo,
        themes_repo=MagicMock(get_all=MagicMock(return_value=[])),
        segments_repo=MagicMock(get_all=MagicMock(return_value=[])),
    )
    result = service.generate_executive_summary()

    assert result is not None
    assert result.available is False
    assert result.output is None
