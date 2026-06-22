"""Analysis repository aggregation helper tests."""

from unittest.mock import MagicMock
from uuid import uuid4

from src.db.repositories.analysis_repo import AnalysisRepository


def _repo() -> AnalysisRepository:
    return AnalysisRepository(client=MagicMock())


def test_sample_reviews_stratified_respects_limit():
    rows = []
    for source in ("playstore", "appstore", "reddit"):
        for sentiment in ("positive", "negative", "neutral"):
            for _ in range(10):
                rows.append(
                    {
                        "review_id": uuid4(),
                        "source": source,
                        "sentiment": sentiment,
                    }
                )

    repo = _repo()
    sampled = repo.sample_reviews_stratified(rows=rows, limit=50)

    assert len(sampled) == 50
    keys = {(row["source"], row["sentiment"]) for row in sampled}
    assert len(keys) >= 3


def test_aggregate_by_segment_counts_sizes():
    rows = [
        {"user_segment": "Music Explorer", "recommendation_complaint": True, "sentiment": "negative"},
        {"user_segment": "Music Explorer", "recommendation_complaint": False, "sentiment": "positive"},
        {"user_segment": "Casual Listener", "recommendation_complaint": False, "sentiment": "neutral"},
    ]

    repo = _repo()
    aggregates = repo.aggregate_by_segment(rows=rows)

    assert aggregates["Music Explorer"].size == 2
    assert aggregates["Music Explorer"].recommendation_complaint_rate == 0.5
    assert aggregates["Casual Listener"].size == 1
    assert aggregates["Power User"].size == 0


def test_sample_negative_reviews_prefers_negative_sentiment():
    rows = [
        {"review_id": uuid4(), "source": "playstore", "sentiment": "positive"},
        {"review_id": uuid4(), "source": "playstore", "sentiment": "negative"},
        {"review_id": uuid4(), "source": "appstore", "sentiment": "mixed"},
    ]

    repo = _repo()
    sampled = repo.sample_negative_reviews(rows=rows, limit=2)

    sentiments = {row["sentiment"] for row in sampled}
    assert "positive" not in sentiments


def test_top_goal_challenge_gaps_ranks_by_frequency():
    rows = [
        {
            "review_id": uuid4(),
            "user_goal": "Find new music",
            "discovery_challenge": "Repetitive playlists",
        },
        {
            "review_id": uuid4(),
            "user_goal": "Find new music",
            "discovery_challenge": "Repetitive playlists",
        },
        {
            "review_id": uuid4(),
            "user_goal": "Relax",
            "discovery_challenge": "Wrong mood",
        },
    ]

    repo = _repo()
    gaps = repo.top_goal_challenge_gaps(rows=rows, limit=10)

    assert gaps[0][0] == "Find new music"
    assert gaps[0][1] == "Repetitive playlists"
    assert gaps[0][2] == 2
