"""Structured output schema for per-review LLM analysis."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SentimentOutput = Literal["positive", "negative", "neutral", "mixed"]

UserSegmentOutput = Literal[
    "Casual Listener",
    "Playlist-Dependent Listener",
    "Music Explorer",
    "Genre Loyalist",
    "Power User",
]


class ReviewAnalysisOutput(BaseModel):
    """Validated LLM response for a single review."""

    sentiment: SentimentOutput
    primary_problem: str = Field(min_length=1)
    recommendation_complaint: bool
    user_goal: str = Field(min_length=1)
    listening_behavior: str = Field(min_length=1)
    user_segment: UserSegmentOutput
    discovery_challenge: str = Field(min_length=1)
    confidence_score: float = Field(ge=0.0, le=1.0)
