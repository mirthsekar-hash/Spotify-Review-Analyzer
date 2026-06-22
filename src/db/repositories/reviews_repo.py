"""Reviews table repository."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from supabase import Client

from src.db.client import get_supabase_client
from src.db.models import NormalizedReview, Review, ReviewSource, UpsertReviewsResult
from src.db.response_utils import first_row, response_data

ReviewSortOrder = Literal["oldest", "newest", "rating_high", "rating_low"]


@dataclass(frozen=True)
class ReviewSearchParams:
    query: str | None = None
    rating: int | None = None
    source: ReviewSource | None = None
    sort_by: ReviewSortOrder = "oldest"


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

    def _apply_search_filters(self, query, params: ReviewSearchParams, *, include_rating: bool = True):
        if params.query:
            escaped = params.query.replace("%", r"\%").replace("_", r"\_")
            query = query.ilike("text", f"%{escaped}%")
        if include_rating and params.rating is not None:
            query = query.eq("rating", params.rating)
        if params.source is not None:
            query = query.eq("source", params.source)
        return query

    def _apply_sort(self, query, sort_by: ReviewSortOrder):
        if sort_by == "newest":
            return query.order("review_date", desc=True).order("created_at", desc=True)
        if sort_by == "rating_high":
            return query.order("rating", desc=True).order("review_date", desc=True)
        if sort_by == "rating_low":
            return query.order("rating", desc=False).order("review_date", desc=True)
        return query.order("review_date", desc=False).order("created_at", desc=False)

    def count_matching(self, params: ReviewSearchParams, *, include_rating: bool = True) -> int:
        query = self._table.select("id", count="exact").limit(1)
        query = self._apply_search_filters(query, params, include_rating=include_rating)
        response = query.execute()
        return response.count or 0

    def get_rating_distribution(self, params: ReviewSearchParams) -> dict[int, int]:
        counts: dict[int, int] = {}
        for star in range(5, 0, -1):
            star_params = ReviewSearchParams(
                query=params.query,
                rating=star,
                source=params.source,
                sort_by=params.sort_by,
            )
            counts[star] = self.count_matching(star_params, include_rating=True)
        return counts

    def search_reviews(
        self,
        params: ReviewSearchParams,
        *,
        offset: int = 0,
        limit: int = 40,
    ) -> list[Review]:
        query = self._table.select("*")
        query = self._apply_search_filters(query, params, include_rating=True)
        query = self._apply_sort(query, params.sort_by)
        query = query.range(offset, offset + limit - 1)
        rows = response_data(query.execute())
        return [Review.from_db(row) for row in rows]

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
