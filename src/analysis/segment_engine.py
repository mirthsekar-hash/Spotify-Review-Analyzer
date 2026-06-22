"""Collective user segmentation summaries from review analysis aggregates."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import Settings, get_settings
from src.analysis.prompts import load_prompt
from src.db.models import SegmentUpsert
from src.db.repositories.analysis_repo import (
    EXPECTED_USER_SEGMENTS,
    AnalysisRepository,
    SegmentAggregate,
)
from src.db.repositories.segments_repo import SegmentsRepository
from src.llm.structured import structured_completion
from src.schemas.review_analysis import UserSegmentOutput
from src.schemas.segments import SegmentSummary, SegmentationOutput

logger = logging.getLogger(__name__)

_FALLBACK_ITEM = "Insufficient evidence in current review sample"


@dataclass
class SegmentEngineResult:
    segments_written: int = 0
    segment_names: list[str] = field(default_factory=list)
    analyzed_review_count: int = 0


class SegmentEngine:
    def __init__(
        self,
        settings: Settings | None = None,
        analysis_repo: AnalysisRepository | None = None,
        segments_repo: SegmentsRepository | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._analysis_repo = analysis_repo or AnalysisRepository()
        self._segments_repo = segments_repo or SegmentsRepository()
        self._system_prompt = load_prompt("segmentation.txt")

    def run(self) -> SegmentEngineResult:
        result = SegmentEngineResult()
        rows = self._analysis_repo.get_collective_rows()
        result.analyzed_review_count = len(rows)

        min_required = self._settings.collective_analysis_threshold
        if len(rows) < min_required:
            raise ValueError(
                f"Need at least {min_required} analyzed reviews for segmentation; found {len(rows)}"
            )

        aggregates = self._analysis_repo.aggregate_by_segment(rows=rows)
        segments_with_data = [segment for segment in aggregates.values() if segment.size > 0]
        if not segments_with_data:
            raise ValueError("No segment aggregates available from analyzed reviews")

        user_content = self._build_user_content(aggregates)
        llm_output = self._call_llm(user_content)
        llm_by_name = {summary.segment_name: summary for summary in llm_output.segments}

        for segment_name in EXPECTED_USER_SEGMENTS:
            aggregate = aggregates[segment_name]
            summary = llm_by_name.get(segment_name)
            upsert = self._build_segment_upsert(aggregate, summary)
            self._segments_repo.upsert(upsert)
            result.segments_written += 1
            result.segment_names.append(segment_name)

        return result

    def _build_user_content(self, aggregates: dict[UserSegmentOutput, SegmentAggregate]) -> str:
        lines: list[str] = []
        for segment_name in EXPECTED_USER_SEGMENTS:
            aggregate = aggregates[segment_name]
            lines.extend(
                [
                    f"SEGMENT: {segment_name}",
                    f"size: {aggregate.size}",
                    f"top user_goals: {', '.join(aggregate.top_user_goals) or 'none'}",
                    f"top listening_behaviors: {', '.join(aggregate.top_listening_behaviors) or 'none'}",
                    f"top discovery_challenges: {', '.join(aggregate.top_discovery_challenges) or 'none'}",
                    f"top primary_problems: {', '.join(aggregate.top_primary_problems) or 'none'}",
                    (
                        "recommendation_complaint_rate: "
                        f"{aggregate.recommendation_complaint_rate * 100:.1f}%"
                    ),
                    f"sentiment breakdown: {aggregate.sentiment_counts}",
                    "---",
                ]
            )
        return "\n".join(lines)

    def _build_segment_upsert(
        self,
        aggregate: SegmentAggregate,
        summary: SegmentSummary | None,
    ) -> SegmentUpsert:
        if summary:
            listening_goals = summary.listening_goals
            discovery_behavior = summary.discovery_behavior
            top_frustrations = summary.top_frustrations
        elif aggregate.size > 0:
            listening_goals = aggregate.top_user_goals or [_FALLBACK_ITEM]
            discovery_behavior = aggregate.top_listening_behaviors or [_FALLBACK_ITEM]
            top_frustrations = (
                aggregate.top_discovery_challenges
                or aggregate.top_primary_problems
                or [_FALLBACK_ITEM]
            )
        else:
            listening_goals = [_FALLBACK_ITEM]
            discovery_behavior = [_FALLBACK_ITEM]
            top_frustrations = [_FALLBACK_ITEM]

        return SegmentUpsert(
            segment_name=aggregate.segment_name,
            size=aggregate.size,
            listening_goals=listening_goals,
            discovery_behavior=discovery_behavior,
            top_frustrations=top_frustrations,
            recommendation_trust_score=compute_recommendation_trust_score(
                aggregate.recommendation_complaint_rate
            ),
        )

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        reraise=True,
    )
    def _call_llm(self, user_content: str) -> SegmentationOutput:
        return structured_completion(
            system_prompt=self._system_prompt,
            user_content=user_content,
            schema_model=SegmentationOutput,
        )


def compute_recommendation_trust_score(recommendation_complaint_rate: float) -> float:
    return round((1.0 - recommendation_complaint_rate) * 100, 1)
