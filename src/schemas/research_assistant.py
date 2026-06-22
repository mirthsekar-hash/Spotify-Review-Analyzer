"""Structured output schema for the RAG Research Assistant."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ReviewSourceOutput = Literal["playstore", "appstore", "reddit"]


class SupportingEvidence(BaseModel):
    """A cited review excerpt returned to the UI."""

    review_id: str = Field(min_length=1)
    excerpt: str = Field(min_length=1, max_length=200)
    source: ReviewSourceOutput
    rating: int | None = Field(default=None, ge=1, le=5)


class ResearchAssistantOutput(BaseModel):
    """Validated LLM response for a strategic product research question."""

    summary: str = Field(min_length=1)
    key_themes: list[str] = Field(default_factory=list)
    root_causes: list[str] = Field(default_factory=list)
    affected_segments: list[str] = Field(default_factory=list)
    supporting_evidence: list[SupportingEvidence] = Field(min_length=1)
    product_opportunities: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
