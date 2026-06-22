"""Structured output schema for collective user segmentation summaries."""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.schemas.review_analysis import UserSegmentOutput


class SegmentSummary(BaseModel):
    """LLM-generated summary for one user segment."""

    segment_name: UserSegmentOutput
    listening_goals: list[str] = Field(min_length=1, max_length=8)
    discovery_behavior: list[str] = Field(min_length=1, max_length=8)
    top_frustrations: list[str] = Field(min_length=1, max_length=8)
    narrative_summary: str = Field(
        min_length=1,
        max_length=600,
        description="Short paragraph synthesizing how this segment discovers music",
    )


class SegmentationOutput(BaseModel):
    """Validated LLM response for per-segment aggregation."""

    segments: list[SegmentSummary] = Field(min_length=1, max_length=5)
