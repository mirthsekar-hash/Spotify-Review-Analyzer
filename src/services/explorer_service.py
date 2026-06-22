"""Collective intelligence explorer queries for Phase 3.7 dashboards."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from src.db.client import check_connection
from src.db.models import RootCause, Segment, Theme, UnmetNeed
from src.db.repositories.analysis_repo import AnalysisRepository
from src.db.repositories.root_causes_repo import RootCausesRepository
from src.db.repositories.segments_repo import SegmentsRepository
from src.db.repositories.themes_repo import ThemesRepository
from src.db.repositories.unmet_needs_repo import UnmetNeedsRepository


@dataclass
class ThemeListItem:
    id: UUID
    theme_name: str
    frequency: int
    impact_score: float | None
    affected_segments: list[str] = field(default_factory=list)
    review_count: int = 0


@dataclass
class ThemesExplorerData:
    themes: list[ThemeListItem] = field(default_factory=list)
    db_connected: bool = False


@dataclass
class ThemeDetailData:
    theme: Theme | None = None
    reviews: list[dict[str, Any]] = field(default_factory=list)
    segment_counts: dict[str, int] = field(default_factory=dict)
    related_root_causes: list[RootCause] = field(default_factory=list)
    related_unmet_needs: list[UnmetNeed] = field(default_factory=list)
    db_connected: bool = False


@dataclass
class SegmentsExplorerData:
    segments: list[Segment] = field(default_factory=list)
    db_connected: bool = False


@dataclass
class RootCauseListItem:
    id: UUID
    root_cause: str
    frequency: int
    affected_segments: list[str] = field(default_factory=list)
    evidence_count: int = 0


@dataclass
class RootCausesExplorerData:
    root_causes: list[RootCauseListItem] = field(default_factory=list)
    db_connected: bool = False


@dataclass
class RootCauseDetailData:
    root_cause: RootCause | None = None
    reviews: list[dict[str, Any]] = field(default_factory=list)
    db_connected: bool = False


@dataclass
class UnmetNeedsExplorerData:
    needs: list[UnmetNeed] = field(default_factory=list)
    db_connected: bool = False


def _theme_to_list_item(theme: Theme) -> ThemeListItem:
    return ThemeListItem(
        id=theme.id,
        theme_name=theme.theme_name,
        frequency=theme.frequency,
        impact_score=theme.impact_score,
        affected_segments=list(theme.affected_segments),
        review_count=len(theme.representative_review_ids),
    )


def _related_by_segments(
    segments: list[str],
    items: list[RootCause],
) -> list[RootCause]:
    if not segments:
        return []
    segment_set = set(segments)
    return [
        item
        for item in items
        if segment_set.intersection(set(item.affected_segments))
    ]


def _top_unmet_needs(items: list[UnmetNeed], *, limit: int = 5) -> list[UnmetNeed]:
    if not items:
        return []
    return sorted(
        items,
        key=lambda item: (-(item.opportunity_score or 0), -item.frequency, item.need),
    )[:limit]


def compute_segment_counts(
    review_ids: list[UUID],
    analysis_rows: list[dict[str, Any]],
) -> dict[str, int]:
    by_review = {str(row.get("review_id")): row for row in analysis_rows}
    counter: Counter[str] = Counter()
    for review_id in review_ids:
        row = by_review.get(str(review_id), {})
        segment = row.get("user_segment")
        if segment:
            counter[str(segment)] += 1
    if counter:
        return dict(counter)

    return {}


class ExplorerService:
    def __init__(
        self,
        themes_repo: ThemesRepository | None = None,
        segments_repo: SegmentsRepository | None = None,
        root_causes_repo: RootCausesRepository | None = None,
        unmet_needs_repo: UnmetNeedsRepository | None = None,
        analysis_repo: AnalysisRepository | None = None,
    ) -> None:
        self._themes_repo = themes_repo or ThemesRepository()
        self._segments_repo = segments_repo or SegmentsRepository()
        self._root_causes_repo = root_causes_repo or RootCausesRepository()
        self._unmet_needs_repo = unmet_needs_repo or UnmetNeedsRepository()
        self._analysis_repo = analysis_repo or AnalysisRepository()

    def get_themes(self) -> ThemesExplorerData:
        if not check_connection():
            return ThemesExplorerData(db_connected=False)

        themes = self._themes_repo.get_all()
        themes.sort(key=lambda item: (-(item.impact_score or 0), -item.frequency, item.theme_name))
        return ThemesExplorerData(
            themes=[_theme_to_list_item(theme) for theme in themes],
            db_connected=True,
        )

    def get_theme_detail(self, theme_id: UUID) -> ThemeDetailData:
        if not check_connection():
            return ThemeDetailData(db_connected=False)

        try:
            payload = self._themes_repo.get_with_reviews(theme_id)
        except ValueError:
            return ThemeDetailData(db_connected=True)

        theme: Theme = payload["theme"]
        reviews: list[dict[str, Any]] = payload.get("reviews") or []
        review_ids = payload.get("review_ids") or theme.representative_review_ids
        analysis_rows = self._analysis_repo.get_fields_by_review_ids(
            list(review_ids),
            columns="review_id, user_segment, sentiment",
        )
        segment_counts = compute_segment_counts(list(review_ids), analysis_rows)
        if not segment_counts and theme.affected_segments:
            segment_counts = {segment: 1 for segment in theme.affected_segments}

        all_root_causes = self._root_causes_repo.get_all()
        all_needs = self._unmet_needs_repo.get_all()
        related_root_causes = _related_by_segments(theme.affected_segments, all_root_causes)
        related_unmet_needs = _top_unmet_needs(all_needs, limit=5)

        return ThemeDetailData(
            theme=theme,
            reviews=reviews,
            segment_counts=segment_counts,
            related_root_causes=related_root_causes,
            related_unmet_needs=related_unmet_needs,
            db_connected=True,
        )

    def get_segments(self) -> SegmentsExplorerData:
        if not check_connection():
            return SegmentsExplorerData(db_connected=False)

        segments = self._segments_repo.get_all()
        return SegmentsExplorerData(segments=segments, db_connected=True)

    def get_root_causes(self) -> RootCausesExplorerData:
        if not check_connection():
            return RootCausesExplorerData(db_connected=False)

        items = [
            RootCauseListItem(
                id=item.id,
                root_cause=item.root_cause,
                frequency=item.frequency,
                affected_segments=list(item.affected_segments),
                evidence_count=len(item.supporting_evidence_ids),
            )
            for item in self._root_causes_repo.get_all()
        ]
        return RootCausesExplorerData(root_causes=items, db_connected=True)

    def get_root_cause_detail(self, root_cause_id: UUID) -> RootCauseDetailData:
        if not check_connection():
            return RootCauseDetailData(db_connected=False)

        try:
            payload = self._root_causes_repo.get_with_evidence(root_cause_id)
        except ValueError:
            return RootCauseDetailData(db_connected=True)

        return RootCauseDetailData(
            root_cause=payload["root_cause"],
            reviews=payload.get("reviews") or [],
            db_connected=True,
        )

    def get_unmet_needs(self) -> UnmetNeedsExplorerData:
        if not check_connection():
            return UnmetNeedsExplorerData(db_connected=False)

        needs = self._unmet_needs_repo.get_all()
        return UnmetNeedsExplorerData(needs=needs, db_connected=True)
