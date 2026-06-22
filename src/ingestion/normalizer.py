"""RawRecord to NormalizedReview pipeline."""

from __future__ import annotations

from src.db.models import NormalizedReview, RawRecord
from src.ingestion.cleaner import clean_text, is_valid_review_text
from src.ingestion.deduplicator import Deduplicator


class Normalizer:
    def __init__(self, deduplicator: Deduplicator | None = None) -> None:
        self._deduplicator = deduplicator or Deduplicator()

    @property
    def deduplicator(self) -> Deduplicator:
        return self._deduplicator

    def raw_to_record(self, raw: RawRecord) -> RawRecord | None:
        cleaned = clean_text(raw.text)
        if not is_valid_review_text(cleaned):
            return None
        return RawRecord(
            source=raw.source,
            text=cleaned,
            rating=raw.rating,
            review_date=raw.review_date,
            metadata=raw.metadata,
        )

    def normalize_one(self, raw: RawRecord) -> NormalizedReview | None:
        prepared = self.raw_to_record(raw)
        if prepared is None or self._deduplicator.is_duplicate_raw(prepared):
            return None
        review = NormalizedReview.from_raw(prepared)
        self._deduplicator.register(review)
        return review

    def normalize_batch(self, records: list[RawRecord]) -> list[NormalizedReview]:
        filtered = self._deduplicator.filter_raw_records(records)
        normalized: list[NormalizedReview] = []
        for raw in filtered:
            review = NormalizedReview.from_raw(raw)
            normalized.append(review)
        return self._deduplicator.filter_normalized(normalized)
