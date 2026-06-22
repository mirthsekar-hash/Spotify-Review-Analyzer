"""Normalizer tests."""

from datetime import datetime, timezone

from src.db.models import RawRecord
from src.ingestion.normalizer import Normalizer


def test_normalize_playstore_raw_record():
    raw = RawRecord(
        source="playstore",
        text="  <b>Great</b>   recommendations   ",
        rating=4,
        review_date=datetime(2024, 3, 1, tzinfo=timezone.utc),
        metadata={"external_id": "abc123", "reviewer_name": "tester"},
    )
    normalizer = Normalizer()
    review = normalizer.normalize_one(raw)

    assert review is not None
    assert review.text == "Great recommendations"
    assert review.source == "playstore"
    assert review.rating == 4
    assert review.metadata["external_id"] == "abc123"


def test_normalize_batch_deduplicates():
    raw = RawRecord(
        source="playstore",
        text="Recommendations feel repetitive",
        rating=2,
        metadata={"external_id": "dup1"},
    )
    duplicate = RawRecord(
        source="playstore",
        text="Recommendations feel repetitive",
        rating=2,
        metadata={"external_id": "dup1"},
    )
    other = RawRecord(
        source="playstore",
        text="Discover Weekly is amazing",
        rating=5,
        metadata={"external_id": "unique1"},
    )

    normalizer = Normalizer()
    result = normalizer.normalize_batch([raw, duplicate, other])
    assert len(result) == 2


def test_spam_filtered():
    raw = RawRecord(source="playstore", text="ok", rating=1)
    normalizer = Normalizer()
    assert normalizer.normalize_one(raw) is None
