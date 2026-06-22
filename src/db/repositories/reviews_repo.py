"""Reviews table repository."""

from __future__ import annotations

from uuid import UUID

from supabase import Client

from src.db.client import get_supabase_client
from src.db.models import NormalizedReview, Review, UpsertReviewsResult
from src.db.response_utils import first_row, response_data


class ReviewsRepository:
    UPSERT_CHUNK_SIZE = 100

    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_supabase_client()
        self._table = self._client.table("reviews")

    def upsert_batch(self, reviews: list[NormalizedReview]) -> UpsertReviewsResult:
        if not reviews:
            return UpsertReviewsResult(attempted=0, stored=0, review_ids=[])

        content_hashes = [review.content_hash for review in reviews]
        existing_hashes = self.get_existing_content_hashes(content_hashes)

        review_ids: list[UUID] = []
        new_review_ids: list[UUID] = []
        for start in range(0, len(reviews), self.UPSERT_CHUNK_SIZE):
            chunk = reviews[start : start + self.UPSERT_CHUNK_SIZE]
            records = [review.to_insert_dict() for review in chunk]
            self._table.upsert(
                records,
                on_conflict="content_hash",
                ignore_duplicates=True,
            ).execute()

            chunk_hashes = [review.content_hash for review in chunk]
            rows = response_data(
                self._table.select("id,content_hash")
                .in_("content_hash", chunk_hashes)
                .execute()
            )
            for row in rows:
                review_id = UUID(row["id"])
                review_ids.append(review_id)
                if row["content_hash"] not in existing_hashes:
                    new_review_ids.append(review_id)

        return UpsertReviewsResult(
            attempted=len(reviews),
            stored=len(review_ids),
            review_ids=review_ids,
            new_review_ids=new_review_ids,
        )

    def get_existing_content_hashes(self, content_hashes: list[str]) -> set[str]:
        if not content_hashes:
            return set()

        unique_hashes = list(dict.fromkeys(content_hashes))
        existing: set[str] = set()
        for start in range(0, len(unique_hashes), self.UPSERT_CHUNK_SIZE):
            chunk = unique_hashes[start : start + self.UPSERT_CHUNK_SIZE]
            rows = response_data(
                self._table.select("content_hash")
                .in_("content_hash", chunk)
                .execute()
            )
            existing.update(row["content_hash"] for row in rows)
        return existing

    def get_by_ids(self, review_ids: list[UUID]) -> list[Review]:
        if not review_ids:
            return []

        reviews: list[Review] = []
        id_strings = [str(review_id) for review_id in review_ids]
        for start in range(0, len(id_strings), self.UPSERT_CHUNK_SIZE):
            chunk = id_strings[start : start + self.UPSERT_CHUNK_SIZE]
            rows = response_data(self._table.select("*").in_("id", chunk).execute())
            reviews.extend(Review.from_db(row) for row in rows)
        return reviews

    def get_by_id(self, review_id: UUID) -> Review | None:
        response = self._table.select("*").eq("id", str(review_id)).limit(1).execute()
        row = first_row(response)
        if not row:
            return None
        return Review.from_db(row)

    def get_unanalyzed(self, limit: int = 100) -> list[Review]:
        rows = response_data(
            self._table.select("*")
            .is_("analyzed_at", "null")
            .order("created_at")
            .limit(limit)
            .execute()
        )
        return [Review.from_db(row) for row in rows]

    def mark_analyzed(self, review_ids: list[UUID]) -> None:
        if not review_ids:
            return
        from datetime import datetime, timezone

        timestamp = datetime.now(timezone.utc).isoformat()
        for review_id in review_ids:
            self._table.update({"analyzed_at": timestamp}).eq("id", str(review_id)).execute()

    def count_by_source(self) -> dict[str, int]:
        rows = response_data(self._table.select("source").execute())
        counts: dict[str, int] = {"playstore": 0, "appstore": 0, "reddit": 0}
        for row in rows:
            source = row["source"]
            counts[source] = counts.get(source, 0) + 1
        return counts

    def count_total(self) -> int:
        response = self._table.select("id", count="exact").limit(1).execute()
        return response.count or 0

    def count_analyzed(self) -> int:
        response = (
            self._table.select("id", count="exact")
            .not_.is_("analyzed_at", "null")
            .limit(1)
            .execute()
        )
        return response.count or 0

    def get_average_rating(self) -> float | None:
        rows = response_data(
            self._table.select("rating").not_.is_("rating", "null").execute()
        )
        ratings = [int(row["rating"]) for row in rows if row.get("rating") is not None]
        if not ratings:
            return None
        return round(sum(ratings) / len(ratings), 2)

    def count_analyzed_by_source(self) -> dict[str, int]:
        rows = response_data(
            self._table.select("source")
            .not_.is_("analyzed_at", "null")
            .execute()
        )
        counts: dict[str, int] = {"playstore": 0, "appstore": 0, "reddit": 0}
        for row in rows:
            source = row.get("source")
            if source in counts:
                counts[source] += 1
        return counts
