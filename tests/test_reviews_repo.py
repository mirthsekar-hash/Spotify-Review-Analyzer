"""Reviews repository tests with mocked Supabase client."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import UUID, uuid4

from src.db.models import NormalizedReview
from src.db.repositories.reviews_repo import ReviewsRepository


def _make_review_row(content_hash: str, review_id: UUID | None = None) -> dict:
    return {
        "id": str(review_id or uuid4()),
        "source": "playstore",
        "text": "Great app but recommendations repeat",
        "rating": 4,
        "review_date": datetime(2024, 5, 1, tzinfo=timezone.utc).isoformat(),
        "metadata": {},
        "content_hash": content_hash,
        "created_at": datetime(2024, 5, 2, tzinfo=timezone.utc).isoformat(),
        "analyzed_at": None,
    }


def test_upsert_batch_deduplicates_by_content_hash():
    review = NormalizedReview(
        source="playstore",
        text="Recommendations are repetitive",
        rating=2,
        review_date=None,
        metadata={},
        content_hash="abc123hash",
    )
    row = _make_review_row(review.content_hash)

    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table

    upsert_chain = MagicMock()
    upsert_chain.execute.return_value = MagicMock(data=[])
    mock_table.upsert.return_value = upsert_chain

    select_chain = MagicMock()
    select_chain.in_.return_value = select_chain
    select_chain.execute.side_effect = [
        MagicMock(data=[]),
        MagicMock(data=[row]),
    ]
    mock_table.select.return_value = select_chain

    repo = ReviewsRepository(client=mock_client)
    result = repo.upsert_batch([review, review])

    mock_table.upsert.assert_called_once()
    upsert_kwargs = mock_table.upsert.call_args.kwargs
    assert upsert_kwargs["on_conflict"] == "content_hash"
    assert upsert_kwargs["ignore_duplicates"] is True
    assert result.attempted == 2
    assert result.stored == 1
    assert len(result.review_ids) == 1
    assert len(result.new_review_ids) == 1


def test_get_unanalyzed_returns_reviews():
    row = _make_review_row("hash123")
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table

    chain = MagicMock()
    chain.is_.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = MagicMock(data=[row])
    mock_table.select.return_value = chain

    repo = ReviewsRepository(client=mock_client)
    reviews = repo.get_unanalyzed(limit=10)

    assert len(reviews) == 1
    assert reviews[0].content_hash == "hash123"
    assert reviews[0].analyzed_at is None
