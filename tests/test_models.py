"""Pydantic model tests."""

from datetime import datetime, timezone

import pytest

from src.db.models import (
    NormalizedReview,
    RawRecord,
    ReviewAnalysisCreate,
    compute_content_hash,
    format_vector,
)


def test_compute_content_hash_is_deterministic():
    text = "Discover Weekly feels repetitive"
    hash_one = compute_content_hash(text, "playstore")
    hash_two = compute_content_hash(text, "playstore")
    assert hash_one == hash_two
    assert len(hash_one) == 64


def test_compute_content_hash_differs_by_source():
    text = "Same review text"
    playstore = compute_content_hash(text, "playstore")
    appstore = compute_content_hash(text, "appstore")
    assert playstore != appstore


def test_raw_record_rejects_invalid_source():
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        RawRecord(source="twitter", text="hello")  # type: ignore[arg-type]


def test_normalized_review_from_raw():
    raw = RawRecord(
        source="reddit",
        text="  Spotify   shuffle   repeats songs  ",
        rating=3,
        review_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        metadata={"subreddit": "spotify"},
    )
    normalized = NormalizedReview.from_raw(raw)
    assert normalized.text == "Spotify shuffle repeats songs"
    assert normalized.source == "reddit"
    assert normalized.content_hash == compute_content_hash(normalized.text, "reddit")


def test_review_analysis_create_serializes_uuid():
    from uuid import uuid4

    review_id = uuid4()
    payload = ReviewAnalysisCreate(
        review_id=review_id,
        sentiment="negative",
        recommendation_complaint=True,
        confidence_score=0.9,
    ).to_insert_dict()
    assert payload["review_id"] == str(review_id)
    assert payload["sentiment"] == "negative"


def test_format_vector():
    assert format_vector([0.1, 0.2, 0.3]) == "[0.1,0.2,0.3]"
