"""Dashboard service unit tests."""

from unittest.mock import MagicMock, patch

from src.services.dashboard_service import (
    DashboardService,
    compute_most_affected_segment,
    compute_recommendation_trust_score,
    compute_sentiment_breakdown,
    compute_source_metrics,
    compute_top_discovery_challenges,
    compute_top_discovery_challenge,
)


def test_compute_sentiment_breakdown_percentages():
    rows = [
        {"sentiment": "positive"},
        {"sentiment": "positive"},
        {"sentiment": "negative"},
        {"sentiment": "neutral"},
    ]
    breakdown = compute_sentiment_breakdown(rows)

    assert breakdown.total == 4
    assert breakdown.positive_pct == 50.0
    assert breakdown.negative_pct == 25.0
    assert breakdown.neutral_pct == 25.0
    assert breakdown.mixed_pct == 0.0


def test_compute_top_discovery_challenge():
    rows = [
        {"discovery_challenge": "Stale recommendations"},
        {"discovery_challenge": "Stale recommendations"},
        {"discovery_challenge": "Poor shuffle"},
    ]
    challenge, count = compute_top_discovery_challenge(rows)
    assert challenge == "Stale recommendations"
    assert count == 2


def test_compute_most_affected_segment():
    rows = [
        {"user_segment": "Music Explorer", "sentiment": "negative"},
        {"user_segment": "Music Explorer", "sentiment": "negative"},
        {"user_segment": "Casual Listener", "sentiment": "positive"},
    ]
    segment, rate = compute_most_affected_segment(rows)
    assert segment == "Music Explorer"
    assert rate == 100.0


def test_compute_recommendation_trust_score():
    rows = [
        {"sentiment": "negative", "recommendation_complaint": True},
        {"sentiment": "negative", "recommendation_complaint": False},
        {"sentiment": "negative", "recommendation_complaint": False},
        {"sentiment": "positive", "recommendation_complaint": True},
    ]
    score = compute_recommendation_trust_score(rows)
    assert score == 66.7


def test_compute_recommendation_trust_score_no_negatives():
    rows = [{"sentiment": "positive", "recommendation_complaint": False}]
    assert compute_recommendation_trust_score(rows) is None


@patch("src.services.dashboard_service.check_connection", return_value=True)
def test_get_executive_summary_aggregates(mock_check):
    reviews_repo = MagicMock()
    reviews_repo.count_total.return_value = 10
    reviews_repo.count_analyzed.return_value = 8
    reviews_repo.get_average_rating.return_value = 3.16

    themes_repo = MagicMock()
    themes_repo.get_all.return_value = [MagicMock(), MagicMock(), MagicMock()]

    analysis_repo = MagicMock()
    analysis_repo.get_dashboard_fields.return_value = [
        {
            "discovery_challenge": "Repetitive playlists",
            "user_segment": "Music Explorer",
            "sentiment": "negative",
            "recommendation_complaint": True,
        },
        {
            "discovery_challenge": "Repetitive playlists",
            "user_segment": "Casual Listener",
            "sentiment": "positive",
            "recommendation_complaint": False,
        },
    ]

    pipeline_repo = MagicMock()
    pipeline_repo.get_latest.return_value = None

    service = DashboardService(
        reviews_repo=reviews_repo,
        analysis_repo=analysis_repo,
        pipeline_runs_repo=pipeline_repo,
        themes_repo=themes_repo,
    )
    summary = service.get_executive_summary()

    assert summary.total_reviews == 10
    assert summary.total_analyzed == 8
    assert summary.pending_analysis == 2
    assert summary.themes_discovered == 3
    assert summary.avg_rating == 3.16
    assert summary.top_discovery_challenge == "Repetitive playlists"
    assert summary.db_connected is True


@patch("src.services.dashboard_service.check_connection", return_value=False)
def test_get_executive_summary_disconnected(mock_check):
    summary = DashboardService().get_executive_summary()
    assert summary.db_connected is False
    assert summary.total_reviews == 0


def test_compute_source_metrics():
    rows = [
        {"source": "playstore", "rating": 4, "sentiment": "negative", "primary_problem": "Stale DW", "recommendation_complaint": True},
        {"source": "playstore", "rating": 2, "sentiment": "negative", "primary_problem": "Stale DW", "recommendation_complaint": False},
        {"source": "playstore", "rating": 5, "sentiment": "positive", "primary_problem": "Great app", "recommendation_complaint": False},
    ]
    metrics = compute_source_metrics("playstore", review_count=10, analyzed_rows=rows)

    assert metrics.review_count == 10
    assert metrics.analyzed_count == 3
    assert metrics.avg_rating == 3.67
    assert metrics.rec_complaint_pct == 33.3
    assert metrics.top_complaints[0] == ("Stale DW", 2)


def test_compute_top_discovery_challenges_groups_segments():
    rows = [
        {"discovery_challenge": "Repetitive playlists", "user_segment": "Explorer", "sentiment": "negative"},
        {"discovery_challenge": "Repetitive playlists", "user_segment": "Explorer", "sentiment": "negative"},
        {"discovery_challenge": "Repetitive playlists", "user_segment": "Casual", "sentiment": "neutral"},
        {"discovery_challenge": "Poor shuffle", "user_segment": "Casual", "sentiment": "negative"},
    ]
    results = compute_top_discovery_challenges(rows, limit=10)

    assert len(results) == 2
    assert results[0].challenge == "Repetitive playlists"
    assert results[0].frequency == 3
    assert results[0].negative_pct == 66.7
    assert "Explorer" in results[0].affected_segments


@patch("src.services.dashboard_service.check_connection", return_value=True)
def test_get_source_analysis(mock_check):
    reviews_repo = MagicMock()
    reviews_repo.count_by_source.return_value = {
        "playstore": 100,
        "appstore": 80,
        "reddit": 50,
    }

    analysis_repo = MagicMock()
    analysis_repo.get_source_analysis_rows.return_value = [
        {
            "source": "playstore",
            "rating": 2,
            "sentiment": "negative",
            "primary_problem": "Bad recommendations",
            "recommendation_complaint": True,
        }
    ]

    service = DashboardService(reviews_repo=reviews_repo, analysis_repo=analysis_repo)
    data = service.get_source_analysis()

    assert data.db_connected is True
    assert data.total_reviews == 230
    assert data.sources["playstore"].review_count == 100
    assert data.sources["playstore"].analyzed_count == 1


@patch("src.services.dashboard_service.check_connection", return_value=True)
def test_get_top_discovery_challenges_service(mock_check):
    analysis_repo = MagicMock()
    analysis_repo.get_dashboard_fields.return_value = [
        {"discovery_challenge": "Algorithm too narrow", "user_segment": "Explorer", "sentiment": "negative"},
    ]
    analysis_repo.count_total.return_value = 1

    data = DashboardService(analysis_repo=analysis_repo).get_top_discovery_challenges()

    assert data.db_connected is True
    assert len(data.challenges) == 1
    assert data.challenges[0].challenge == "Algorithm too narrow"
