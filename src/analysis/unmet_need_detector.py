"""Unmet need detection from goal–challenge gap analysis."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from uuid import UUID

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import Settings, get_settings
from src.analysis.prompts import load_prompt
from src.db.models import UnmetNeedUpsert
from src.db.repositories.analysis_repo import AnalysisRepository
from src.db.repositories.unmet_needs_repo import UnmetNeedsRepository
from src.llm.structured import structured_completion
from src.schemas.unmet_needs import UnmetNeedItem, UnmetNeedsOutput

logger = logging.getLogger(__name__)


@dataclass
class UnmetNeedDetectorResult:
    needs_written: int = 0
    need_names: list[str] = field(default_factory=list)
    analyzed_review_count: int = 0
    gap_pairs_used: int = 0


class UnmetNeedDetector:
    def __init__(
        self,
        settings: Settings | None = None,
        analysis_repo: AnalysisRepository | None = None,
        unmet_needs_repo: UnmetNeedsRepository | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._analysis_repo = analysis_repo or AnalysisRepository()
        self._unmet_needs_repo = unmet_needs_repo or UnmetNeedsRepository()
        self._system_prompt = load_prompt("unmet_needs.txt")

    def run(self) -> UnmetNeedDetectorResult:
        result = UnmetNeedDetectorResult()
        rows = self._analysis_repo.get_collective_rows()
        result.analyzed_review_count = len(rows)

        min_required = self._settings.collective_analysis_threshold
        if len(rows) < min_required:
            raise ValueError(
                f"Need at least {min_required} analyzed reviews for unmet need detection; found {len(rows)}"
            )

        gaps = self._analysis_repo.top_goal_challenge_gaps(rows=rows, limit=30)
        if not gaps:
            raise ValueError("No user_goal / discovery_challenge gap pairs found in analyzed reviews")

        result.gap_pairs_used = len(gaps)
        sample = _sample_reviews_from_gaps(gaps, limit=40)
        sample_ids = {UUID(str(row["review_id"])) for row in sample if row.get("review_id")}

        user_content = self._build_user_content(gaps, sample, len(rows))
        output = self._call_llm(user_content)
        opportunity_scores = compute_opportunity_scores(output.unmet_needs)

        for item in output.unmet_needs:
            valid_review_ids = [
                review_id
                for review_id in item.supporting_review_ids
                if review_id in sample_ids
            ]
            if len(valid_review_ids) < 2:
                logger.warning(
                    "Skipping unmet need %s: fewer than 2 valid supporting review IDs in sample",
                    item.need,
                )
                continue

            if not item.suggested_ai_solutions:
                logger.warning("Skipping unmet need %s: no suggested AI solutions", item.need)
                continue

            upsert = UnmetNeedUpsert(
                need=item.need,
                frequency=item.frequency,
                opportunity_score=opportunity_scores.get(item.need),
                supporting_review_ids=valid_review_ids,
                suggested_ai_solutions=item.suggested_ai_solutions,
            )
            self._unmet_needs_repo.upsert(upsert)
            result.needs_written += 1
            result.need_names.append(item.need)

        if result.needs_written < 5:
            raise RuntimeError(
                f"Unmet need detection produced only {result.needs_written} valid needs; need at least 5"
            )

        return result

    def _build_user_content(
        self,
        gaps: list[tuple[str, str, int, list[dict]]],
        sample: list[dict],
        total_reviews: int,
    ) -> str:
        lines = [
            f"TOTAL ANALYZED REVIEWS: {total_reviews}",
            "",
            "GAP ANALYSIS — user_goal vs discovery_challenge (top pairs by frequency):",
        ]
        for goal, challenge, count, _ in gaps:
            lines.append(f"- goal: {goal} | challenge: {challenge} | count: {count}")

        lines.extend(["", "SUPPORTING SAMPLE REVIEWS:"])
        for row in sample:
            lines.append(
                "\n".join(
                    [
                        f"review_id: {row.get('review_id')}",
                        f"segment: {row.get('user_segment')}",
                        f"sentiment: {row.get('sentiment')}",
                        f"user_goal: {row.get('user_goal')}",
                        f"discovery_challenge: {row.get('discovery_challenge')}",
                        f"text: {row.get('text')}",
                    ]
                )
            )
            lines.append("---")

        return "\n".join(lines)

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        reraise=True,
    )
    def _call_llm(self, user_content: str) -> UnmetNeedsOutput:
        return structured_completion(
            system_prompt=self._system_prompt,
            user_content=user_content,
            schema_model=UnmetNeedsOutput,
        )


def _sample_reviews_from_gaps(
    gaps: list[tuple[str, str, int, list[dict]]],
    limit: int = 40,
) -> list[dict]:
    seen: set[UUID] = set()
    sample: list[dict] = []
    for _, _, _, matching_rows in gaps:
        for row in matching_rows:
            review_id = row.get("review_id")
            if not review_id:
                continue
            parsed_id = UUID(str(review_id))
            if parsed_id in seen:
                continue
            seen.add(parsed_id)
            sample.append(row)
            if len(sample) >= limit:
                return sample
    return sample


def compute_opportunity_scores(needs: list[UnmetNeedItem]) -> dict[str, float]:
    raw_scores: dict[str, float] = {}
    for need in needs:
        segment_breadth = len(need.affected_segments)
        raw_scores[need.need] = need.frequency * need.severity_score * segment_breadth

    max_raw = max(raw_scores.values()) if raw_scores else 0.0
    if max_raw <= 0:
        return {name: 0.0 for name in raw_scores}

    return {
        name: round((score / max_raw) * 100, 1)
        for name, score in raw_scores.items()
    }
