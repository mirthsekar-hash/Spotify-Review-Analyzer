"""Database domain models and helpers."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

ReviewSource = Literal["playstore", "appstore", "reddit"]
Sentiment = Literal["positive", "negative", "neutral", "mixed"]
PipelineStatus = Literal["running", "success", "partial", "failed"]

VALID_SOURCES = {"playstore", "appstore", "reddit"}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def compute_content_hash(text: str, source: ReviewSource) -> str:
    normalized = normalize_text(text).lower()
    payload = f"{normalized}:{source}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class RawRecord(BaseModel):
    """Raw record from a source adapter before normalization."""

    source: ReviewSource
    text: str
    rating: int | None = None
    review_date: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        if value not in VALID_SOURCES:
            raise ValueError(f"Invalid source: {value}")
        return value


class NormalizedReview(BaseModel):
    """Canonical review ready for Supabase upsert."""

    source: ReviewSource
    text: str
    rating: int | None = None
    review_date: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    content_hash: str

    @classmethod
    def from_raw(cls, raw: RawRecord) -> NormalizedReview:
        cleaned_text = normalize_text(raw.text)
        return cls(
            source=raw.source,
            text=cleaned_text,
            rating=raw.rating,
            review_date=raw.review_date,
            metadata=raw.metadata,
            content_hash=compute_content_hash(cleaned_text, raw.source),
        )

    def to_insert_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "text": self.text,
            "rating": self.rating,
            "review_date": self.review_date.isoformat() if self.review_date else None,
            "metadata": self.metadata,
            "content_hash": self.content_hash,
        }


class Review(BaseModel):
    id: UUID
    source: ReviewSource
    text: str
    rating: int | None = None
    review_date: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    content_hash: str
    created_at: datetime | None = None
    analyzed_at: datetime | None = None

    @classmethod
    def from_db(cls, row: dict[str, Any]) -> Review:
        return cls.model_validate(row)


class ReviewAnalysis(BaseModel):
    id: UUID
    review_id: UUID
    sentiment: Sentiment | None = None
    primary_problem: str | None = None
    recommendation_complaint: bool = False
    user_goal: str | None = None
    listening_behavior: str | None = None
    user_segment: str | None = None
    discovery_challenge: str | None = None
    confidence_score: float | None = None
    created_at: datetime | None = None

    @classmethod
    def from_db(cls, row: dict[str, Any]) -> ReviewAnalysis:
        return cls.model_validate(row)


class ReviewAnalysisCreate(BaseModel):
    review_id: UUID
    sentiment: Sentiment | None = None
    primary_problem: str | None = None
    recommendation_complaint: bool = False
    user_goal: str | None = None
    listening_behavior: str | None = None
    user_segment: str | None = None
    discovery_challenge: str | None = None
    confidence_score: float | None = None

    def to_insert_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class EmbeddingRecord(BaseModel):
    id: UUID
    review_id: UUID
    embedding: list[float]
    model: str
    created_at: datetime | None = None

    @classmethod
    def from_db(cls, row: dict[str, Any]) -> EmbeddingRecord:
        data = dict(row)
        if isinstance(data.get("embedding"), str):
            data["embedding"] = _parse_vector_string(data["embedding"])
        return cls.model_validate(data)


class VectorSearchResult(BaseModel):
    review_id: UUID
    similarity: float


class UpsertReviewsResult(BaseModel):
    attempted: int
    stored: int
    review_ids: list[UUID]
    new_review_ids: list[UUID] = Field(default_factory=list)


class Theme(BaseModel):
    id: UUID
    theme_name: str
    frequency: int = 0
    impact_score: float | None = None
    representative_review_ids: list[UUID] = Field(default_factory=list)
    affected_segments: list[str] = Field(default_factory=list)
    updated_at: datetime | None = None

    @classmethod
    def from_db(cls, row: dict[str, Any]) -> Theme:
        return cls.model_validate(row)


class ThemeUpsert(BaseModel):
    theme_name: str
    frequency: int = Field(ge=0)
    impact_score: float | None = None
    representative_review_ids: list[UUID] = Field(default_factory=list)
    affected_segments: list[str] = Field(default_factory=list)

    def to_upsert_dict(self) -> dict[str, Any]:
        return {
            "theme_name": self.theme_name,
            "frequency": self.frequency,
            "impact_score": self.impact_score,
            "representative_review_ids": [str(rid) for rid in self.representative_review_ids],
            "affected_segments": self.affected_segments,
        }


class Segment(BaseModel):
    id: UUID
    segment_name: str
    size: int = 0
    listening_goals: list[str] = Field(default_factory=list)
    discovery_behavior: list[str] = Field(default_factory=list)
    top_frustrations: list[str] = Field(default_factory=list)
    recommendation_trust_score: float | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_db(cls, row: dict[str, Any]) -> Segment:
        data = dict(row)
        for field in ("listening_goals", "discovery_behavior", "top_frustrations"):
            if data.get(field) is None:
                data[field] = []
        return cls.model_validate(data)


class SegmentUpsert(BaseModel):
    segment_name: str
    size: int = Field(ge=0)
    listening_goals: list[str] = Field(default_factory=list)
    discovery_behavior: list[str] = Field(default_factory=list)
    top_frustrations: list[str] = Field(default_factory=list)
    recommendation_trust_score: float | None = None

    def to_upsert_dict(self) -> dict[str, Any]:
        return {
            "segment_name": self.segment_name,
            "size": self.size,
            "listening_goals": self.listening_goals,
            "discovery_behavior": self.discovery_behavior,
            "top_frustrations": self.top_frustrations,
            "recommendation_trust_score": self.recommendation_trust_score,
        }


class RootCause(BaseModel):
    id: UUID
    root_cause: str
    frequency: int = 0
    supporting_evidence_ids: list[UUID] = Field(default_factory=list)
    affected_segments: list[str] = Field(default_factory=list)
    updated_at: datetime | None = None

    @classmethod
    def from_db(cls, row: dict[str, Any]) -> RootCause:
        return cls.model_validate(row)


class RootCauseUpsert(BaseModel):
    root_cause: str
    frequency: int = Field(ge=0)
    supporting_evidence_ids: list[UUID] = Field(default_factory=list)
    affected_segments: list[str] = Field(default_factory=list)

    def to_upsert_dict(self) -> dict[str, Any]:
        return {
            "root_cause": self.root_cause,
            "frequency": self.frequency,
            "supporting_evidence_ids": [str(rid) for rid in self.supporting_evidence_ids],
            "affected_segments": self.affected_segments,
        }


class UnmetNeed(BaseModel):
    id: UUID
    need: str
    frequency: int = 0
    opportunity_score: float | None = None
    supporting_review_ids: list[UUID] = Field(default_factory=list)
    suggested_ai_solutions: list[str] = Field(default_factory=list)
    updated_at: datetime | None = None

    @classmethod
    def from_db(cls, row: dict[str, Any]) -> UnmetNeed:
        data = dict(row)
        if data.get("suggested_ai_solutions") is None:
            data["suggested_ai_solutions"] = []
        return cls.model_validate(data)


class UnmetNeedUpsert(BaseModel):
    need: str
    frequency: int = Field(ge=0)
    opportunity_score: float | None = None
    supporting_review_ids: list[UUID] = Field(default_factory=list)
    suggested_ai_solutions: list[str] = Field(default_factory=list)

    def to_upsert_dict(self) -> dict[str, Any]:
        return {
            "need": self.need,
            "frequency": self.frequency,
            "opportunity_score": self.opportunity_score,
            "supporting_review_ids": [str(rid) for rid in self.supporting_review_ids],
            "suggested_ai_solutions": self.suggested_ai_solutions,
        }


class InterviewInsight(BaseModel):
    id: UUID
    insight: str
    linked_theme_id: UUID | None = None
    validation_pct: float | None = None
    confidence_score: float | None = None
    notes: str | None = None
    created_at: datetime | None = None

    @classmethod
    def from_db(cls, row: dict[str, Any]) -> InterviewInsight:
        return cls.model_validate(row)


def format_vector(values: list[float]) -> str:
    """Format a vector for pgvector columns via PostgREST."""
    return "[" + ",".join(str(float(v)) for v in values) + "]"


def _parse_vector_string(value: str) -> list[float]:
    stripped = value.strip().lstrip("[").rstrip("]")
    if not stripped:
        return []
    return [float(part) for part in stripped.split(",")]
