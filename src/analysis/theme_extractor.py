"""Collective theme extraction from aggregated review analysis."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from uuid import UUID

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import Settings, get_settings
from src.analysis.prompts import load_prompt
from src.db.models import ThemeUpsert
from src.db.repositories.analysis_repo import AnalysisRepository
from src.db.repositories.themes_repo import ThemesRepository
from src.llm.structured import structured_completion
from src.schemas.themes import ThemeExtractionOutput, ThemeItem

logger = logging.getLogger(__name__)


@dataclass
class ThemeExtractionResult:
    themes_written: int = 0
    theme_names: list[str] = field(default_factory=list)
    analyzed_review_count: int = 0


class ThemeExtractor:
    def __init__(
        self,
        settings: Settings | None = None,
        analysis_repo: AnalysisRepository | None = None,
        themes_repo: ThemesRepository | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._analysis_repo = analysis_repo or AnalysisRepository()
        self._themes_repo = themes_repo or ThemesRepository()
        self._system_prompt = load_prompt("theme_extraction.txt")

    def run(self) -> ThemeExtractionResult:
        result = ThemeExtractionResult()
        rows = self._analysis_repo.get_collective_rows()
        result.analyzed_review_count = len(rows)

        min_required = self._settings.collective_analysis_threshold
        if len(rows) < min_required:
            raise ValueError(
                f"Need at least {min_required} analyzed reviews for theme extraction; found {len(rows)}"
            )

        discovery_stats = self._analysis_repo.top_field_frequencies("discovery_challenge", limit=30)
        problem_stats = self._analysis_repo.top_field_frequencies("primary_problem", limit=30)
        sample = self._analysis_repo.sample_reviews_stratified(rows=rows, limit=50)
        sample_ids = {UUID(str(row["review_id"])) for row in sample if row.get("review_id")}

        user_content = self._build_user_content(discovery_stats, problem_stats, sample, len(rows))
        output = self._call_llm(user_content)
        analysis_by_review = {
            UUID(str(row["review_id"])): row
            for row in rows
            if row.get("review_id")
        }
        impact_scores = compute_impact_scores(output.themes, analysis_by_review)

        for theme in output.themes:
            valid_review_ids = [
                review_id
                for review_id in theme.representative_review_ids
                if review_id in sample_ids
            ]
            if len(valid_review_ids) < 3:
                logger.warning(
                    "Skipping theme %s: fewer than 3 valid representative review IDs in sample",
                    theme.theme_name,
                )
                continue

            upsert = ThemeUpsert(
                theme_name=theme.theme_name,
                frequency=theme.frequency,
                impact_score=impact_scores.get(theme.theme_name),
                representative_review_ids=valid_review_ids,
                affected_segments=[str(segment) for segment in theme.affected_segments],
            )
            stored = self._themes_repo.upsert(upsert)
            self._themes_repo.replace_theme_reviews(stored.id, valid_review_ids)
            result.themes_written += 1
            result.theme_names.append(theme.theme_name)

        if result.themes_written == 0:
            raise RuntimeError("Theme extraction produced no valid themes to persist")

        return result

    def _build_user_content(
        self,
        discovery_stats: list[tuple[str, int]],
        problem_stats: list[tuple[str, int]],
        sample: list[dict],
        total_reviews: int,
    ) -> str:
        lines = [
            f"TOTAL ANALYZED REVIEWS: {total_reviews}",
            "",
            "FREQUENCY STATS — discovery_challenge (top 30):",
        ]
        for value, count in discovery_stats:
            lines.append(f"- {value}: {count}")

        lines.extend(["", "FREQUENCY STATS — primary_problem (top 30):"])
        for value, count in problem_stats:
            lines.append(f"- {value}: {count}")

        lines.extend(["", "SAMPLE REVIEWS:"])
        for row in sample:
            lines.append(
                "\n".join(
                    [
                        f"review_id: {row.get('review_id')}",
                        f"source: {row.get('source')}",
                        f"sentiment: {row.get('sentiment')}",
                        f"segment: {row.get('user_segment')}",
                        f"discovery_challenge: {row.get('discovery_challenge')}",
                        f"primary_problem: {row.get('primary_problem')}",
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
    def _call_llm(self, user_content: str) -> ThemeExtractionOutput:
        return structured_completion(
            system_prompt=self._system_prompt,
            user_content=user_content,
            schema_model=ThemeExtractionOutput,
        )


def compute_impact_scores(
    themes: list[ThemeItem],
    analysis_by_review: dict[UUID, dict],
) -> dict[str, float]:
    raw_scores: dict[str, float] = {}
    for theme in themes:
        evidence = theme.representative_review_ids
        if not evidence:
            raw_scores[theme.theme_name] = 0.0
            continue

        negative_count = 0
        complaint_count = 0
        for review_id in evidence:
            row = analysis_by_review.get(review_id, {})
            if row.get("sentiment") == "negative":
                negative_count += 1
            if row.get("recommendation_complaint"):
                complaint_count += 1

        evidence_size = len(evidence)
        neg_rate = negative_count / evidence_size
        complaint_rate = complaint_count / evidence_size
        raw_scores[theme.theme_name] = theme.frequency * neg_rate * complaint_rate

    max_raw = max(raw_scores.values()) if raw_scores else 0.0
    if max_raw <= 0:
        return {name: 0.0 for name in raw_scores}

    return {
        name: round((score / max_raw) * 100, 1)
        for name, score in raw_scores.items()
    }
