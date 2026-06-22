"""Interview validation service for Dashboard 9 (Phase 4.4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.db.client import check_connection
from src.db.models import InterviewInsight, Theme
from src.schemas.interview_insight import InterviewInsightCreate, InterviewInsightUpdate
from src.db.repositories.interview_insights_repo import InterviewInsightsRepository
from src.db.repositories.themes_repo import ThemesRepository


@dataclass
class InterviewInsightRow:
    id: UUID
    insight: str
    linked_theme_id: UUID | None = None
    linked_theme_name: str | None = None
    review_evidence_count: int = 0
    validation_pct: float | None = None
    confidence_score: float | None = None
    notes: str | None = None
    created_at: datetime | None = None


@dataclass
class InterviewValidationData:
    insights: list[InterviewInsightRow] = field(default_factory=list)
    themes: list[Theme] = field(default_factory=list)
    db_connected: bool = False


def compute_suggested_confidence(validation_pct: float | None, review_count: int) -> float | None:
    """Blend interview validation % with review evidence depth (0–1)."""
    if validation_pct is None:
        return None
    evidence_factor = min(review_count / 10.0, 1.0)
    return round((validation_pct / 100.0) * 0.7 + evidence_factor * 0.3, 2)


class InterviewValidationService:
    def __init__(
        self,
        insights_repo: InterviewInsightsRepository | None = None,
        themes_repo: ThemesRepository | None = None,
    ) -> None:
        self._insights_repo = insights_repo or InterviewInsightsRepository()
        self._themes_repo = themes_repo or ThemesRepository()

    def get_validation_data(self) -> InterviewValidationData:
        if not check_connection():
            return InterviewValidationData(db_connected=False)

        themes = self._themes_repo.get_all()
        theme_by_id = {theme.id: theme for theme in themes}
        insights = self._insights_repo.get_all()
        rows = [self._to_row(insight, theme_by_id) for insight in insights]

        return InterviewValidationData(
            insights=rows,
            themes=themes,
            db_connected=True,
        )

    def create_insight(self, payload: InterviewInsightCreate) -> InterviewInsightRow:
        if payload.confidence_score is None and payload.validation_pct is not None:
            review_count = 0
            if payload.linked_theme_id:
                review_count = self._themes_repo.count_linked_reviews(payload.linked_theme_id)
            suggested = compute_suggested_confidence(payload.validation_pct, review_count)
            if suggested is not None:
                payload = payload.model_copy(update={"confidence_score": suggested})

        stored = self._insights_repo.insert(payload)
        theme_by_id = {theme.id: theme for theme in self._themes_repo.get_all()}
        return self._to_row(stored, theme_by_id)

    def update_insight(
        self,
        insight_id: UUID,
        payload: InterviewInsightUpdate,
    ) -> InterviewInsightRow:
        stored = self._insights_repo.update(insight_id, payload)
        theme_by_id = {theme.id: theme for theme in self._themes_repo.get_all()}
        return self._to_row(stored, theme_by_id)

    def delete_insight(self, insight_id: UUID) -> None:
        self._insights_repo.delete(insight_id)

    def _to_row(
        self,
        insight: InterviewInsight,
        theme_by_id: dict[UUID, Theme],
    ) -> InterviewInsightRow:
        theme = theme_by_id.get(insight.linked_theme_id) if insight.linked_theme_id else None
        review_count = 0
        if insight.linked_theme_id:
            review_count = self._themes_repo.count_linked_reviews(insight.linked_theme_id)

        return InterviewInsightRow(
            id=insight.id,
            insight=insight.insight,
            linked_theme_id=insight.linked_theme_id,
            linked_theme_name=theme.theme_name if theme else None,
            review_evidence_count=review_count,
            validation_pct=insight.validation_pct,
            confidence_score=insight.confidence_score,
            notes=insight.notes,
            created_at=insight.created_at,
        )
