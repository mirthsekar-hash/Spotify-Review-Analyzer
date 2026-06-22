"""Root cause analysis from themes and negative review clusters."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from uuid import UUID

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import Settings, get_settings
from src.analysis.prompts import load_prompt
from src.db.models import RootCauseUpsert, Theme
from src.db.repositories.analysis_repo import AnalysisRepository
from src.db.repositories.root_causes_repo import RootCausesRepository
from src.db.repositories.themes_repo import ThemesRepository
from src.llm.structured import structured_completion
from src.schemas.root_causes import RootCauseOutput

logger = logging.getLogger(__name__)


@dataclass
class RootCauseEngineResult:
    root_causes_written: int = 0
    root_cause_names: list[str] = field(default_factory=list)
    analyzed_review_count: int = 0
    themes_used: int = 0


class RootCauseEngine:
    def __init__(
        self,
        settings: Settings | None = None,
        analysis_repo: AnalysisRepository | None = None,
        themes_repo: ThemesRepository | None = None,
        root_causes_repo: RootCausesRepository | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._analysis_repo = analysis_repo or AnalysisRepository()
        self._themes_repo = themes_repo or ThemesRepository()
        self._root_causes_repo = root_causes_repo or RootCausesRepository()
        self._system_prompt = load_prompt("root_cause.txt")

    def run(self) -> RootCauseEngineResult:
        result = RootCauseEngineResult()
        rows = self._analysis_repo.get_collective_rows()
        result.analyzed_review_count = len(rows)

        min_required = self._settings.collective_analysis_threshold
        if len(rows) < min_required:
            raise ValueError(
                f"Need at least {min_required} analyzed reviews for root cause analysis; found {len(rows)}"
            )

        themes = self._themes_repo.get_all()
        if not themes:
            raise ValueError("No themes found — run theme extraction before root cause analysis")

        result.themes_used = len(themes)
        negative_sample = self._analysis_repo.sample_negative_reviews(rows=rows, limit=40)
        sample_ids = {UUID(str(row["review_id"])) for row in negative_sample if row.get("review_id")}

        user_content = self._build_user_content(themes, negative_sample, len(rows))
        output = self._call_llm(user_content)

        for item in output.root_causes:
            valid_evidence_ids = [
                review_id
                for review_id in item.supporting_evidence_ids
                if review_id in sample_ids
            ]
            if not valid_evidence_ids:
                logger.warning(
                    "Skipping root cause %s: no valid supporting evidence IDs in sample",
                    item.root_cause,
                )
                continue

            upsert = RootCauseUpsert(
                root_cause=item.root_cause,
                frequency=item.frequency,
                supporting_evidence_ids=valid_evidence_ids,
                affected_segments=[str(segment) for segment in item.affected_segments],
            )
            self._root_causes_repo.upsert(upsert)
            result.root_causes_written += 1
            result.root_cause_names.append(item.root_cause)

        if result.root_causes_written < 5:
            raise RuntimeError(
                f"Root cause analysis produced only {result.root_causes_written} valid causes; need at least 5"
            )

        return result

    def _build_user_content(
        self,
        themes: list[Theme],
        negative_sample: list[dict],
        total_reviews: int,
    ) -> str:
        lines = [
            f"TOTAL ANALYZED REVIEWS: {total_reviews}",
            "",
            "TOP THEMES:",
        ]
        for theme in themes:
            segments = ", ".join(theme.affected_segments) if theme.affected_segments else "unknown"
            lines.append(
                f"- {theme.theme_name} (frequency={theme.frequency}, segments={segments})"
            )

        lines.extend(["", "NEGATIVE REVIEW SAMPLE:"])
        for row in negative_sample:
            lines.append(
                "\n".join(
                    [
                        f"review_id: {row.get('review_id')}",
                        f"source: {row.get('source')}",
                        f"sentiment: {row.get('sentiment')}",
                        f"segment: {row.get('user_segment')}",
                        f"primary_problem: {row.get('primary_problem')}",
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
    def _call_llm(self, user_content: str) -> RootCauseOutput:
        return structured_completion(
            system_prompt=self._system_prompt,
            user_content=user_content,
            schema_model=RootCauseOutput,
        )
