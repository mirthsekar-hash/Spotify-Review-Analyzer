"""Retriever tests with mocked embeddings and repositories."""

from unittest.mock import MagicMock
from uuid import uuid4

from src.db.models import VectorSearchResult
from src.rag.retriever import Retriever, extract_keywords


def _eligible_row(
    *,
    text: str = "Discover Weekly repeats the same songs every week.",
    primary_problem: str = "Repetitive playlists",
    discovery_challenge: str = "Stale recommendations",
    confidence_score: float = 0.9,
):
    review_id = uuid4()
    return {
        "review_id": review_id,
        "source": "playstore",
        "text": text,
        "rating": 2,
        "sentiment": "negative",
        "primary_problem": primary_problem,
        "discovery_challenge": discovery_challenge,
        "user_goal": "Discover new music",
        "listening_behavior": "Uses Discover Weekly",
        "user_segment": "Music Explorer",
        "recommendation_complaint": True,
        "confidence_score": confidence_score,
    }


def test_extract_keywords_filters_stopwords():
    keywords = extract_keywords("Why do users struggle to discover new music?")
    assert "discover" not in keywords
    assert "struggle" in keywords
    assert "music" not in keywords


def test_retriever_merges_vector_and_keyword_hits():
    vector_row = _eligible_row(
        text="Shuffle keeps playing the same tracks.",
        primary_problem="Shuffle repetition",
        discovery_challenge="Lack of variety",
    )
    keyword_row = _eligible_row(
        text="Radio mode is useless for discovery.",
        primary_problem="Users repeat the same playlists",
        discovery_challenge="Cannot find new artists",
    )
    low_confidence_row = _eligible_row(confidence_score=0.2)

    settings = MagicMock(rag_min_confidence=0.5, rag_top_k=15)
    embeddings_repo = MagicMock()
    embeddings_repo.vector_search.return_value = [
        VectorSearchResult(review_id=vector_row["review_id"], similarity=0.88)
    ]

    analysis_repo = MagicMock()
    analysis_repo.get_rag_eligible_rows.return_value = [vector_row, keyword_row]

    retriever = Retriever(
        settings=settings,
        embeddings_repo=embeddings_repo,
        analysis_repo=analysis_repo,
    )
    retriever.embed_query = MagicMock(return_value=[0.1] * 768)

    result = retriever.retrieve("Why do users repeat playlists?")

    assert len(result.reviews) >= 2
    assert result.vector_hit_count == 1
    assert result.keyword_hit_count >= 1
    assert result.eligible_review_count == 2
    assert all(review.review_id != low_confidence_row["review_id"] for review in result.reviews)


def test_retriever_excludes_low_confidence_vector_hits():
    row = _eligible_row(confidence_score=0.9)
    low_row = _eligible_row(confidence_score=0.3)

    settings = MagicMock(rag_min_confidence=0.5, rag_top_k=15)
    embeddings_repo = MagicMock()
    embeddings_repo.vector_search.return_value = [
        VectorSearchResult(review_id=low_row["review_id"], similarity=0.95),
        VectorSearchResult(review_id=row["review_id"], similarity=0.80),
    ]

    analysis_repo = MagicMock()
    analysis_repo.get_rag_eligible_rows.return_value = [row]

    retriever = Retriever(
        settings=settings,
        embeddings_repo=embeddings_repo,
        analysis_repo=analysis_repo,
    )
    retriever.embed_query = MagicMock(return_value=[0.1] * 768)

    result = retriever.retrieve("What causes repetitive listening?")

    review_ids = {review.review_id for review in result.reviews}
    assert row["review_id"] in review_ids
    assert low_row["review_id"] not in review_ids


def test_retriever_returns_at_least_three_reviews_when_available():
    rows = [_eligible_row(text=f"Review text {index}") for index in range(5)]

    settings = MagicMock(rag_min_confidence=0.5, rag_top_k=15)
    embeddings_repo = MagicMock()
    embeddings_repo.vector_search.return_value = [
        VectorSearchResult(review_id=row["review_id"], similarity=0.9 - index * 0.05)
        for index, row in enumerate(rows[:3])
    ]

    analysis_repo = MagicMock()
    analysis_repo.get_rag_eligible_rows.return_value = rows

    retriever = Retriever(
        settings=settings,
        embeddings_repo=embeddings_repo,
        analysis_repo=analysis_repo,
    )
    retriever.embed_query = MagicMock(return_value=[0.1] * 768)

    result = retriever.retrieve("What recommendation complaints are increasing?")

    assert len(result.reviews) >= 3
