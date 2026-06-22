"""Review analysis table repository."""

from __future__ import annotations

import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from uuid import UUID

from typing import Any

from supabase import Client

from src.db.client import get_supabase_client
from src.db.models import ReviewAnalysis, ReviewAnalysisCreate, Sentiment
from src.db.response_utils import first_insert_row, first_row, response_data
from src.schemas.review_analysis import UserSegmentOutput

EXPECTED_USER_SEGMENTS: tuple[UserSegmentOutput, ...] = (
    "Casual Listener",
    "Playlist-Dependent Listener",
    "Music Explorer",
    "Genre Loyalist",
    "Power User",
)


@dataclass
class SegmentAggregate:
    segment_name: UserSegmentOutput
    size: int
    top_user_goals: list[str] = field(default_factory=list)
    top_listening_behaviors: list[str] = field(default_factory=list)
    top_discovery_challenges: list[str] = field(default_factory=list)
    top_primary_problems: list[str] = field(default_factory=list)
    recommendation_complaint_rate: float = 0.0
    sentiment_counts: dict[str, int] = field(default_factory=dict)


class AnalysisRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_supabase_client()
        self._table = self._client.table("review_analysis")

    def insert(self, analysis: ReviewAnalysisCreate) -> ReviewAnalysis:
        response = self._table.insert(analysis.to_insert_dict()).execute()
        row = first_insert_row(response, context="review_analysis insert")
        return ReviewAnalysis.from_db(row)

    def get_by_review_id(self, review_id: UUID) -> ReviewAnalysis | None:
        response = (
            self._table.select("*")
            .eq("review_id", str(review_id))
            .limit(1)
            .execute()
        )
        row = first_row(response)
        if not row:
            return None
        return ReviewAnalysis.from_db(row)

    def aggregate_sentiment(self) -> dict[Sentiment, int]:
        rows = response_data(self._table.select("sentiment").execute())
        counts: dict[Sentiment, int] = {
            "positive": 0,
            "negative": 0,
            "neutral": 0,
            "mixed": 0,
        }
        for row in rows:
            sentiment = row.get("sentiment")
            if sentiment in counts:
                counts[sentiment] += 1
        return counts

    def count_total(self) -> int:
        response = self._table.select("id", count="exact").limit(1).execute()
        return response.count or 0

    def get_fields_by_review_ids(
        self,
        review_ids: list[UUID],
        columns: str = "review_id, user_segment, sentiment",
    ) -> list[dict[str, Any]]:
        if not review_ids:
            return []
        id_strings = [str(review_id) for review_id in review_ids]
        all_rows: list[dict[str, Any]] = []
        chunk_size = 100
        for start in range(0, len(id_strings), chunk_size):
            chunk = id_strings[start : start + chunk_size]
            response = self._table.select(columns).in_("review_id", chunk).execute()
            all_rows.extend(response_data(response))
        return all_rows

    def get_dashboard_fields(self) -> list[dict[str, Any]]:
        return self._fetch_paginated(
            "discovery_challenge, user_segment, sentiment, recommendation_complaint"
        )

    def get_source_analysis_rows(self) -> list[dict[str, Any]]:
        raw_rows = self._fetch_paginated(
            "sentiment, primary_problem, recommendation_complaint, discovery_challenge, "
            "user_segment, reviews!inner(source, rating)"
        )
        return [_flatten_source_row(row) for row in raw_rows]

    def get_collective_rows(self) -> list[dict[str, Any]]:
        raw_rows = self._fetch_paginated(
            "review_id, sentiment, primary_problem, recommendation_complaint, user_goal, "
            "listening_behavior, user_segment, discovery_challenge, confidence_score, "
            "reviews!inner(id, source, text, rating)"
        )
        return [_flatten_collective_row(row) for row in raw_rows]

    def get_rag_eligible_rows(self, min_confidence: float) -> list[dict[str, Any]]:
        """Return analyzed reviews meeting the RAG confidence threshold."""
        return [
            row
            for row in self.get_collective_rows()
            if (row.get("confidence_score") or 0.0) >= min_confidence
        ]

    def top_field_frequencies(self, field: str, limit: int = 30) -> list[tuple[str, int]]:
        counter: Counter[str] = Counter()
        for row in self.get_collective_rows():
            value = row.get(field)
            if value and str(value).strip():
                counter[str(value).strip()] += 1
        return counter.most_common(limit)

    def sample_reviews_stratified(
        self,
        rows: list[dict[str, Any]] | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        pool = rows if rows is not None else self.get_collective_rows()
        if len(pool) <= limit:
            return list(pool)

        buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in pool:
            key = (row.get("sentiment") or "unknown", row.get("source") or "unknown")
            buckets[key].append(row)

        for bucket in buckets.values():
            random.shuffle(bucket)

        keys = list(buckets.keys())
        sampled: list[dict[str, Any]] = []
        index = 0
        while len(sampled) < limit and any(buckets[key] for key in keys):
            key = keys[index % len(keys)]
            if buckets[key]:
                sampled.append(buckets[key].pop())
            index += 1
            if index > limit * max(len(keys), 1) * 3:
                break
        return sampled

    def aggregate_by_segment(
        self,
        rows: list[dict[str, Any]] | None = None,
    ) -> dict[UserSegmentOutput, SegmentAggregate]:
        pool = rows if rows is not None else self.get_collective_rows()
        grouped: dict[UserSegmentOutput, list[dict[str, Any]]] = {
            segment: [] for segment in EXPECTED_USER_SEGMENTS
        }
        for row in pool:
            segment = row.get("user_segment")
            if segment in grouped:
                grouped[segment].append(row)

        aggregates: dict[UserSegmentOutput, SegmentAggregate] = {}
        for segment_name, segment_rows in grouped.items():
            complaints = sum(1 for row in segment_rows if row.get("recommendation_complaint"))
            size = len(segment_rows)
            aggregates[segment_name] = SegmentAggregate(
                segment_name=segment_name,
                size=size,
                top_user_goals=_top_values(segment_rows, "user_goal"),
                top_listening_behaviors=_top_values(segment_rows, "listening_behavior"),
                top_discovery_challenges=_top_values(segment_rows, "discovery_challenge"),
                top_primary_problems=_top_values(segment_rows, "primary_problem"),
                recommendation_complaint_rate=(complaints / size) if size else 0.0,
                sentiment_counts=dict(Counter(row.get("sentiment") or "unknown" for row in segment_rows)),
            )
        return aggregates

    def sample_negative_reviews(
        self,
        rows: list[dict[str, Any]] | None = None,
        limit: int = 40,
    ) -> list[dict[str, Any]]:
        pool = rows if rows is not None else self.get_collective_rows()
        negative_pool = [
            row for row in pool if row.get("sentiment") in ("negative", "mixed")
        ]
        if not negative_pool:
            negative_pool = pool
        return self.sample_reviews_stratified(rows=negative_pool, limit=limit)

    def top_goal_challenge_gaps(
        self,
        rows: list[dict[str, Any]] | None = None,
        limit: int = 30,
    ) -> list[tuple[str, str, int, list[dict[str, Any]]]]:
        pool = rows if rows is not None else self.get_collective_rows()
        gap_rows: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in pool:
            goal = row.get("user_goal")
            challenge = row.get("discovery_challenge")
            if goal and challenge:
                key = (str(goal).strip(), str(challenge).strip())
                gap_rows[key].append(row)

        ranked = sorted(gap_rows.items(), key=lambda item: len(item[1]), reverse=True)[:limit]
        return [
            (goal, challenge, len(matching_rows), matching_rows)
            for (goal, challenge), matching_rows in ranked
        ]

    def _fetch_paginated(self, columns: str, page_size: int = 1000) -> list[dict[str, Any]]:
        all_rows: list[dict[str, Any]] = []
        offset = 0

        while True:
            response = (
                self._table.select(columns)
                .range(offset, offset + page_size - 1)
                .execute()
            )
            if response is None:
                break
            rows = response_data(response)
            all_rows.extend(rows)
            if len(rows) < page_size:
                break
            offset += page_size

        return all_rows


def _top_values(rows: list[dict[str, Any]], field: str, limit: int = 5) -> list[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        value = row.get(field)
        if value and str(value).strip():
            counter[str(value).strip()] += 1
    return [value for value, _ in counter.most_common(limit)]


def _flatten_collective_row(row: dict[str, Any]) -> dict[str, Any]:
    reviews = row.get("reviews") or {}
    if isinstance(reviews, list):
        reviews = reviews[0] if reviews else {}

    review_id = row.get("review_id") or reviews.get("id")
    return {
        "review_id": review_id,
        "source": reviews.get("source"),
        "text": reviews.get("text"),
        "rating": reviews.get("rating"),
        "sentiment": row.get("sentiment"),
        "primary_problem": row.get("primary_problem"),
        "recommendation_complaint": row.get("recommendation_complaint"),
        "user_goal": row.get("user_goal"),
        "listening_behavior": row.get("listening_behavior"),
        "user_segment": row.get("user_segment"),
        "discovery_challenge": row.get("discovery_challenge"),
        "confidence_score": row.get("confidence_score"),
    }


def _flatten_source_row(row: dict[str, Any]) -> dict[str, Any]:
    reviews = row.get("reviews") or {}
    if isinstance(reviews, list):
        reviews = reviews[0] if reviews else {}

    return {
        "source": reviews.get("source"),
        "rating": reviews.get("rating"),
        "sentiment": row.get("sentiment"),
        "primary_problem": row.get("primary_problem"),
        "recommendation_complaint": row.get("recommendation_complaint"),
        "discovery_challenge": row.get("discovery_challenge"),
        "user_segment": row.get("user_segment"),
    }
