"""Build LLM context bundles for the Research Assistant."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from src.db.models import RootCause, Segment, Theme, UnmetNeed
from src.db.repositories.root_causes_repo import RootCausesRepository
from src.db.repositories.segments_repo import SegmentsRepository
from src.db.repositories.themes_repo import ThemesRepository
from src.db.repositories.unmet_needs_repo import UnmetNeedsRepository
from src.rag.retriever import RetrievedReview, RetrievalResult

DEFAULT_MAX_TOKENS = 6000
THEME_LIMIT = 5
ROOT_CAUSE_LIMIT = 3
UNMET_NEED_LIMIT = 3


@dataclass
class RagContext:
    question: str
    reviews_block: str = ""
    themes_block: str = ""
    segments_block: str = ""
    root_causes_block: str = ""
    unmet_needs_block: str = ""
    token_estimate: int = 0
    retrieved_review_ids: list[UUID] = field(default_factory=list)


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 characters per token)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def _truncate_text(text: str, max_chars: int) -> str:
    cleaned = text.strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."


def format_review_entry(review: RetrievedReview, max_text_chars: int = 500) -> str:
    rating_text = review.rating if review.rating is not None else "unknown"
    similarity_text = (
        f"{review.similarity:.3f}" if review.similarity is not None else "n/a"
    )
    return (
        f"[Review #{review.review_id} | {review.source} | rating {rating_text} | "
        f"similarity {similarity_text}]\n"
        f"Segment: {review.user_segment or 'unknown'}\n"
        f"Sentiment: {review.sentiment or 'unknown'}\n"
        f"Primary problem: {review.primary_problem or 'n/a'}\n"
        f"Discovery challenge: {review.discovery_challenge or 'n/a'}\n"
        f"Text: {_truncate_text(review.text, max_text_chars)}"
    )


def format_themes(themes: list[Theme]) -> str:
    if not themes:
        return "No collective themes available."
    lines = []
    for theme in themes[:THEME_LIMIT]:
        segments = ", ".join(theme.affected_segments) or "n/a"
        impact = f"{theme.impact_score:.1f}" if theme.impact_score is not None else "n/a"
        lines.append(
            f"- {theme.theme_name} (frequency={theme.frequency}, impact={impact}, "
            f"segments={segments})"
        )
    return "\n".join(lines)


def format_segments(segments: list[Segment]) -> str:
    if not segments:
        return "No segment profiles available."
    lines = []
    for segment in segments:
        frustrations = "; ".join(segment.top_frustrations[:3]) or "n/a"
        lines.append(
            f"- {segment.segment_name} (size={segment.size}, "
            f"top frustrations={frustrations})"
        )
    return "\n".join(lines)


def format_root_causes(root_causes: list[RootCause]) -> str:
    if not root_causes:
        return "No root causes available."
    lines = []
    for item in root_causes[:ROOT_CAUSE_LIMIT]:
        segments = ", ".join(item.affected_segments) or "n/a"
        lines.append(
            f"- {item.root_cause} (frequency={item.frequency}, segments={segments})"
        )
    return "\n".join(lines)


def format_unmet_needs(needs: list[UnmetNeed]) -> str:
    if not needs:
        return "No unmet needs available."
    lines = []
    for need in needs[:UNMET_NEED_LIMIT]:
        score = f"{need.opportunity_score:.2f}" if need.opportunity_score is not None else "n/a"
        lines.append(f"- {need.need} (frequency={need.frequency}, opportunity={score})")
    return "\n".join(lines)


def trim_reviews_to_budget(
    reviews: list[RetrievedReview],
    *,
    max_tokens: int,
    reserved_tokens: int,
) -> tuple[list[str], list[UUID]]:
    budget = max(0, max_tokens - reserved_tokens)
    formatted: list[str] = []
    review_ids: list[UUID] = []
    used_tokens = 0

    for review in reviews:
        entry = format_review_entry(review)
        entry_tokens = estimate_tokens(entry)
        if formatted and used_tokens + entry_tokens > budget:
            break
        formatted.append(entry)
        review_ids.append(review.review_id)
        used_tokens += entry_tokens

    if not formatted and reviews:
        entry = format_review_entry(reviews[0], max_text_chars=300)
        formatted.append(entry)
        review_ids.append(reviews[0].review_id)

    return formatted, review_ids


class ContextBuilder:
    def __init__(
        self,
        themes_repo: ThemesRepository | None = None,
        segments_repo: SegmentsRepository | None = None,
        root_causes_repo: RootCausesRepository | None = None,
        unmet_needs_repo: UnmetNeedsRepository | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self._themes_repo = themes_repo or ThemesRepository()
        self._segments_repo = segments_repo or SegmentsRepository()
        self._root_causes_repo = root_causes_repo or RootCausesRepository()
        self._unmet_needs_repo = unmet_needs_repo or UnmetNeedsRepository()
        self._max_tokens = max_tokens

    def build(self, retrieval: RetrievalResult) -> RagContext:
        themes = self._themes_repo.get_all()
        segments = self._segments_repo.get_all()
        root_causes = self._root_causes_repo.get_all()
        unmet_needs = self._unmet_needs_repo.get_all()

        themes_block = format_themes(themes)
        segments_block = format_segments(segments)
        root_causes_block = format_root_causes(root_causes)
        unmet_needs_block = format_unmet_needs(unmet_needs)

        reserved_tokens = estimate_tokens(
            "\n".join(
                [
                    retrieval.question,
                    themes_block,
                    segments_block,
                    root_causes_block,
                    unmet_needs_block,
                ]
            )
        )

        review_entries, review_ids = trim_reviews_to_budget(
            retrieval.reviews,
            max_tokens=self._max_tokens,
            reserved_tokens=reserved_tokens,
        )
        reviews_block = "\n\n".join(review_entries) if review_entries else "No review evidence retrieved."

        total_text = "\n".join(
            [
                retrieval.question,
                reviews_block,
                themes_block,
                segments_block,
                root_causes_block,
                unmet_needs_block,
            ]
        )

        return RagContext(
            question=retrieval.question,
            reviews_block=reviews_block,
            themes_block=themes_block,
            segments_block=segments_block,
            root_causes_block=root_causes_block,
            unmet_needs_block=unmet_needs_block,
            token_estimate=estimate_tokens(total_text),
            retrieved_review_ids=review_ids,
        )

    def build_user_content(self, context: RagContext) -> str:
        return (
            f"QUESTION:\n{context.question}\n\n"
            f"RETRIEVED REVIEWS:\n{context.reviews_block}\n\n"
            f"TOP THEMES:\n{context.themes_block}\n\n"
            f"SEGMENT PROFILES:\n{context.segments_block}\n\n"
            f"ROOT CAUSES:\n{context.root_causes_block}\n\n"
            f"UNMET NEEDS:\n{context.unmet_needs_block}"
        )
