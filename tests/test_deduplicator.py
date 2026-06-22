"""Deduplicator tests."""

from src.db.models import NormalizedReview, RawRecord, compute_content_hash
from src.ingestion.deduplicator import Deduplicator


def test_content_hash_dedup():
    deduper = Deduplicator()
    raw = RawRecord(source="playstore", text="Same review text", rating=3)
    assert not deduper.is_duplicate_raw(raw)

    review = NormalizedReview.from_raw(raw)
    deduper.register(review)

    duplicate = RawRecord(source="playstore", text="Same review text", rating=3)
    assert deduper.is_duplicate_raw(duplicate)


def test_different_source_not_duplicate():
    deduper = Deduplicator()
    playstore = RawRecord(source="playstore", text="Same review text for both sources", rating=3)
    appstore = RawRecord(source="appstore", text="Same review text for both sources", rating=3)

    review = NormalizedReview.from_raw(playstore)
    deduper.register(review)

    assert deduper.is_duplicate_raw(appstore) is False


def test_external_id_dedup():
    deduper = Deduplicator()
    first = RawRecord(
        source="reddit",
        text="First post about shuffle",
        metadata={"external_id": "t3_abc"},
    )
    second = RawRecord(
        source="reddit",
        text="Different text but same post id",
        metadata={"external_id": "t3_abc"},
    )

    review = NormalizedReview.from_raw(first)
    deduper.register(review)
    assert deduper.is_duplicate_raw(second) is True


def test_hash_differs_for_different_text():
    text_a = compute_content_hash("Text A", "playstore")
    text_b = compute_content_hash("Text B", "playstore")
    assert text_a != text_b
