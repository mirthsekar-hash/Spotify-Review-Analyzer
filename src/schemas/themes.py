"""Structured output schema for collective theme extraction."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from src.schemas.review_analysis import UserSegmentOutput


class ThemeItem(BaseModel):
    """A synthesized discovery theme backed by review evidence."""

    theme_name: str = Field(min_length=1, max_length=200)
    frequency: int = Field(ge=1, description="Estimated count of reviews supporting this theme")
    representative_review_ids: list[UUID] = Field(
        min_length=3,
        description="Review UUIDs from the provided sample that support this theme",
    )
    affected_segments: list[UserSegmentOutput] = Field(
        min_length=1,
        description="User segments most affected by this theme",
    )
    summary: str = Field(
        min_length=1,
        max_length=500,
        description="One-sentence description of the discovery pain point",
    )


class ThemeExtractionOutput(BaseModel):
    """Validated LLM response for theme extraction (5–15 themes)."""

    themes: list[ThemeItem] = Field(min_length=5, max_length=15)
