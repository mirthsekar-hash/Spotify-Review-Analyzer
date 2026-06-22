"""Input schemas for interview validation CRUD."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class InterviewInsightCreate(BaseModel):
    insight: str = Field(min_length=1)
    linked_theme_id: UUID | None = None
    validation_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    notes: str | None = None

    def to_insert_dict(self) -> dict:
        payload = self.model_dump(mode="json")
        if payload.get("linked_theme_id") is None:
            payload.pop("linked_theme_id", None)
        return payload


class InterviewInsightUpdate(BaseModel):
    insight: str | None = Field(default=None, min_length=1)
    linked_theme_id: UUID | None = None
    validation_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    notes: str | None = None

    def to_update_dict(self) -> dict:
        payload = self.model_dump(mode="json", exclude_unset=True)
        if "linked_theme_id" in payload and payload["linked_theme_id"] is None:
            payload["linked_theme_id"] = None
        return payload
