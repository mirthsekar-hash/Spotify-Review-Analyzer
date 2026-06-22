"""Structured output schema for unmet need detection."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from src.schemas.review_analysis import UserSegmentOutput


class UnmetNeedItem(BaseModel):
    """A gap between stated user goals and discovery outcomes."""

    need: str = Field(min_length=1, max_length=300)
    frequency: int = Field(ge=1, description="Estimated reviews expressing this unmet need")
    supporting_review_ids: list[UUID] = Field(
        min_length=2,
        description="Review UUIDs from the provided sample evidencing this need",
    )
    affected_segments: list[UserSegmentOutput] = Field(min_length=1)
    severity_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Subjective severity of the unmet need (0=minor, 1=critical)",
    )
    suggested_ai_solutions: list[str] = Field(
        min_length=1,
        max_length=5,
        description="Actionable AI-powered product ideas to address the need",
    )


class UnmetNeedsOutput(BaseModel):
    """Validated LLM response for unmet need detection (5–10 needs)."""

    unmet_needs: list[UnmetNeedItem] = Field(min_length=5, max_length=10)
