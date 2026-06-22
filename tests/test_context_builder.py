"""Context builder tests."""

from unittest.mock import MagicMock
from uuid import uuid4

from src.db.models import RootCause, Segment, Theme, UnmetNeed
from src.rag.context_builder import ContextBuilder, estimate_tokens, trim_reviews_to_budget
from src.rag.retriever import RetrievedReview, RetrievalResult


def _retrieved_review(text: str) -> RetrievedReview:
    return RetrievedReview(
        review_id=uuid4(),
        source="playstore",
        text=text,
        rating=2,
        similarity=0.85,
        sentiment="negative",
        primary_problem="Stale playlists",
        discovery_challenge="Repetitive recommendations",
        user_segment="Music Explorer",
        confidence_score=0.9,
    )


def test_trim_reviews_to_budget_respects_token_limit():
    reviews = [_retrieved_review("x" * 2000) for _ in range(10)]
    entries, review_ids = trim_reviews_to_budget(
        reviews,
        max_tokens=600,
        reserved_tokens=200,
    )
    assert len(entries) < len(reviews)
    assert len(entries) == len(review_ids)
    total_tokens = estimate_tokens("\n\n".join(entries))
    assert total_tokens <= 400


def test_context_builder_stays_within_token_budget():
    reviews = [_retrieved_review(f"Review body {index} " * 40) for index in range(15)]
    retrieval = RetrievalResult(question="Why is discovery hard?", reviews=reviews)

    themes_repo = MagicMock()
    themes_repo.get_all.return_value = [
        Theme(
            id=uuid4(),
            theme_name="Stale Discover Weekly",
            frequency=12,
            impact_score=80.0,
            affected_segments=["Music Explorer"],
        )
    ]
    segments_repo = MagicMock()
    segments_repo.get_all.return_value = [
        Segment(
            id=uuid4(),
            segment_name="Music Explorer",
            size=20,
            top_frustrations=["Same songs every week"],
        )
    ]
    root_causes_repo = MagicMock()
    root_causes_repo.get_all.return_value = [
        RootCause(
            id=uuid4(),
            root_cause="Algorithm overfits past listening",
            frequency=8,
            affected_segments=["Music Explorer"],
        )
    ]
    unmet_needs_repo = MagicMock()
    unmet_needs_repo.get_all.return_value = [
        UnmetNeed(
            id=uuid4(),
            need="Fresh weekly discovery mixes",
            frequency=5,
            opportunity_score=0.8,
        )
    ]

    builder = ContextBuilder(
        themes_repo=themes_repo,
        segments_repo=segments_repo,
        root_causes_repo=root_causes_repo,
        unmet_needs_repo=unmet_needs_repo,
        max_tokens=6000,
    )
    context = builder.build(retrieval)

    assert context.token_estimate <= 6000
    assert context.retrieved_review_ids
    user_content = builder.build_user_content(context)
    assert "QUESTION:" in user_content
    assert "TOP THEMES:" in user_content
    assert "ROOT CAUSES:" in user_content
