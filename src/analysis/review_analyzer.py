"""Per-review LLM analysis using structured JSON output."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from uuid import UUID

from app.config import Settings, get_settings
from src.analysis.prompts import load_prompt
from src.db.models import Review, ReviewAnalysisCreate
from src.db.repositories.analysis_repo import AnalysisRepository
from src.llm.errors import LlmQuotaExceededError, format_llm_error
from src.llm.structured import structured_completion
from src.schemas.review_analysis import ReviewAnalysisOutput

logger = logging.getLogger(__name__)


@dataclass
class ReviewAnalysisBatchResult:
    attempted: int = 0
    analyzed: int = 0
    skipped: int = 0
    failed: int = 0
    failed_review_ids: list[UUID] = field(default_factory=list)
    analyzed_review_ids: list[UUID] = field(default_factory=list)
    quota_exceeded: bool = False
    quota_message: str | None = None


class ReviewAnalyzer:
    def __init__(
        self,
        settings: Settings | None = None,
        analysis_repo: AnalysisRepository | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._analysis_repo = analysis_repo or AnalysisRepository()
        self._system_prompt = load_prompt("review_analysis.txt")

    def build_user_content(self, review: Review) -> str:
        rating_text = review.rating if review.rating is not None else "unknown"
        return (
            f"Source: {review.source}\n"
            f"Rating: {rating_text}\n"
            f"Review text:\n{review.text}"
        )

    def _call_llm(self, review: Review) -> ReviewAnalysisOutput:
        return structured_completion(
            system_prompt=self._system_prompt,
            user_content=self.build_user_content(review),
            schema_model=ReviewAnalysisOutput,
        )

    def analyze_one(self, review: Review) -> ReviewAnalysisCreate:
        if self._analysis_repo.get_by_review_id(review.id):
            raise ValueError(f"Review {review.id} already analyzed")

        output = self._call_llm(review)
        return ReviewAnalysisCreate(
            review_id=review.id,
            sentiment=output.sentiment,
            primary_problem=output.primary_problem,
            recommendation_complaint=output.recommendation_complaint,
            user_goal=output.user_goal,
            listening_behavior=output.listening_behavior,
            user_segment=output.user_segment,
            discovery_challenge=output.discovery_challenge,
            confidence_score=output.confidence_score,
        )

    def analyze_and_store(self, review: Review) -> ReviewAnalysisCreate | None:
        if self._analysis_repo.get_by_review_id(review.id):
            logger.debug("Skipping already analyzed review %s", review.id)
            return None

        try:
            analysis = self.analyze_one(review)
            self._analysis_repo.insert(analysis)
            return analysis
        except Exception as exc:
            logger.error(
                "Failed to analyze review %s: %s",
                review.id,
                format_llm_error(exc),
            )
            raise

    def analyze_batch(self, reviews: list[Review]) -> ReviewAnalysisBatchResult:
        result = ReviewAnalysisBatchResult()
        batch_size = self._settings.analysis_batch_size
        request_delay = self._settings.analysis_request_delay_seconds

        for index in range(0, len(reviews), batch_size):
            batch = reviews[index : index + batch_size]
            for review in batch:
                result.attempted += 1
                if self._analysis_repo.get_by_review_id(review.id):
                    result.skipped += 1
                    result.analyzed_review_ids.append(review.id)
                    continue
                try:
                    stored = self.analyze_and_store(review)
                    if stored:
                        result.analyzed += 1
                        result.analyzed_review_ids.append(review.id)
                except LlmQuotaExceededError as exc:
                    result.failed += 1
                    result.failed_review_ids.append(review.id)
                    result.quota_exceeded = True
                    result.quota_message = str(exc)
                    logger.error("Stopping analysis batch — quota exceeded: %s", exc)
                    return result
                except Exception:
                    result.failed += 1
                    result.failed_review_ids.append(review.id)

                if request_delay > 0:
                    time.sleep(request_delay)

            if index + batch_size < len(reviews):
                time.sleep(1)

        return result
