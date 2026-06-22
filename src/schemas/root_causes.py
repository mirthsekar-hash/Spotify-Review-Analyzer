"""Structured output schema for root cause analysis."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from src.schemas.review_analysis import UserSegmentOutput


class RootCauseItem(BaseModel):
    """A causal factor underlying discovery complaints (distinct from descriptive themes)."""

    root_cause: str = Field(min_length=1, max_length=300)
    frequency: int = Field(ge=1, description="Estimated number of reviews evidencing this cause")
    supporting_evidence_ids: list[UUID] = Field(
        min_length=1,
        description="Review UUIDs from the provided sample supporting this root cause",
    )
    affected_segments: list[UserSegmentOutput] = Field(min_length=1)
    causal_explanation: str = Field(
        min_length=1,
        max_length=500,
        description="Why this cause leads to discovery failures (not just what users said)",
    )


class RootCauseOutput(BaseModel):
    """Validated LLM response for root cause mining (5–10 causes)."""

    root_causes: list[RootCauseItem] = Field(min_length=5, max_length=10)
