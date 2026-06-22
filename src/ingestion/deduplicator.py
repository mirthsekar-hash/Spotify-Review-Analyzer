"""In-memory and content-hash deduplication."""

from __future__ import annotations

from src.db.models import NormalizedReview, RawRecord, compute_content_hash
from src.ingestion.cleaner import clean_text, is_valid_review_text


class Deduplicator:
    def __init__(self) -> None:
        self._content_hashes: set[str] = set()
        self._external_ids: set[str] = set()

    def seed_from_hashes(self, hashes: set[str]) -> None:
        self._content_hashes.update(hashes)

    def seed_from_external_ids(self, external_ids: set[str]) -> None:
        self._external_ids.update(external_ids)

    def is_duplicate_raw(self, record: RawRecord) -> bool:
        cleaned = clean_text(record.text)
        if not is_valid_review_text(cleaned):
            return True

        content_hash = compute_content_hash(cleaned, record.source)
        if content_hash in self._content_hashes:
            return True

        external_id = record.metadata.get("external_id")
        if external_id and external_id in self._external_ids:
            return True

        return False

    def register(self, review: NormalizedReview) -> None:
        self._content_hashes.add(review.content_hash)
        external_id = review.metadata.get("external_id")
        if external_id:
            self._external_ids.add(str(external_id))

    def filter_raw_records(self, records: list[RawRecord]) -> list[RawRecord]:
        unique: list[RawRecord] = []
        for record in records:
            if self.is_duplicate_raw(record):
                continue
            unique.append(record)
        return unique

    def filter_normalized(self, reviews: list[NormalizedReview]) -> list[NormalizedReview]:
        unique: list[NormalizedReview] = []
        for review in reviews:
            if review.content_hash in self._content_hashes:
                continue
            external_id = review.metadata.get("external_id")
            if external_id and str(external_id) in self._external_ids:
                continue
            self.register(review)
            unique.append(review)
        return unique
