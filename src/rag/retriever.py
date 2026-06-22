"""Hybrid RAG retriever: vector search + keyword boost with confidence filtering."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from uuid import UUID

from app.config import Settings, get_settings
from src.db.repositories.analysis_repo import AnalysisRepository
from src.db.repositories.embeddings_repo import EmbeddingsRepository
from src.llm.embedding_factory import create_embedding_provider

logger = logging.getLogger(__name__)

_STOPWORDS = frozenset(
    {
        "about",
        "and",
        "are",
        "biggest",
        "can",
        "cause",
        "causes",
        "challenge",
        "challenges",
        "complaint",
        "complaints",
        "discover",
        "discovery",
        "does",
        "for",
        "from",
        "how",
        "increasing",
        "music",
        "new",
        "the",
        "their",
        "users",
        "user",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "with",
        "spotify",
    }
)


@dataclass
class RetrievedReview:
    review_id: UUID
    source: str
    text: str
    rating: int | None
    similarity: float | None = None
    sentiment: str | None = None
    primary_problem: str | None = None
    discovery_challenge: str | None = None
    user_segment: str | None = None
    user_goal: str | None = None
    listening_behavior: str | None = None
    recommendation_complaint: bool = False
    confidence_score: float | None = None
    retrieval_source: str = "vector"


@dataclass
class RetrievalResult:
    question: str
    reviews: list[RetrievedReview] = field(default_factory=list)
    vector_hit_count: int = 0
    keyword_hit_count: int = 0
    eligible_review_count: int = 0


def extract_keywords(question: str) -> list[str]:
    """Extract meaningful terms from a user question for keyword boosting."""
    words = re.findall(r"[a-zA-Z]{3,}", question.lower())
    seen: set[str] = set()
    keywords: list[str] = []
    for word in words:
        if word in _STOPWORDS or word in seen:
            continue
        seen.add(word)
        keywords.append(word)
    return keywords


def _row_matches_keywords(row: dict, keywords: list[str]) -> bool:
    if not keywords:
        return False
    haystack = " ".join(
        str(row.get(field) or "")
        for field in ("primary_problem", "discovery_challenge", "user_goal", "text")
    ).lower()
    return any(keyword in haystack for keyword in keywords)


def _row_to_retrieved(
    row: dict,
    *,
    similarity: float | None,
    retrieval_source: str,
) -> RetrievedReview:
    return RetrievedReview(
        review_id=UUID(str(row["review_id"])),
        source=str(row.get("source") or "unknown"),
        text=str(row.get("text") or ""),
        rating=row.get("rating"),
        similarity=similarity,
        sentiment=row.get("sentiment"),
        primary_problem=row.get("primary_problem"),
        discovery_challenge=row.get("discovery_challenge"),
        user_segment=row.get("user_segment"),
        user_goal=row.get("user_goal"),
        listening_behavior=row.get("listening_behavior"),
        recommendation_complaint=bool(row.get("recommendation_complaint")),
        confidence_score=row.get("confidence_score"),
        retrieval_source=retrieval_source,
    )


class Retriever:
    def __init__(
        self,
        settings: Settings | None = None,
        embeddings_repo: EmbeddingsRepository | None = None,
        analysis_repo: AnalysisRepository | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._embeddings_repo = embeddings_repo or EmbeddingsRepository()
        self._analysis_repo = analysis_repo or AnalysisRepository()
        self._embedding_provider = create_embedding_provider(self._settings)

    def embed_query(self, question: str) -> list[float]:
        vectors = self._embedding_provider.embed_texts([question.strip()])
        if not vectors:
            raise ValueError("No embedding returned for query")
        return vectors[0]

    def retrieve(self, question: str) -> RetrievalResult:
        eligible_rows = self._analysis_repo.get_rag_eligible_rows(
            self._settings.rag_min_confidence
        )
        rows_by_id = {str(row["review_id"]): row for row in eligible_rows}
        result = RetrievalResult(
            question=question.strip(),
            eligible_review_count=len(eligible_rows),
        )

        if not eligible_rows:
            logger.warning("No RAG-eligible reviews found (confidence >= %s)", self._settings.rag_min_confidence)
            return result

        vector_hits: list[RetrievedReview] = []
        try:
            query_embedding = self.embed_query(question)
            search_results = self._embeddings_repo.vector_search(
                query_embedding,
                match_count=self._settings.rag_top_k,
            )
            for hit in search_results:
                row = rows_by_id.get(str(hit.review_id))
                if not row:
                    continue
                vector_hits.append(
                    _row_to_retrieved(
                        row,
                        similarity=hit.similarity,
                        retrieval_source="vector",
                    )
                )
        except Exception as exc:
            logger.error("Vector search failed, falling back to keyword-only retrieval: %s", exc)

        keywords = extract_keywords(question)
        keyword_hits: list[RetrievedReview] = []
        for row in eligible_rows:
            review_id = str(row["review_id"])
            if any(item.review_id == UUID(review_id) for item in vector_hits):
                continue
            if _row_matches_keywords(row, keywords):
                keyword_hits.append(
                    _row_to_retrieved(
                        row,
                        similarity=None,
                        retrieval_source="keyword",
                    )
                )

        keyword_hits.sort(
            key=lambda item: (item.confidence_score or 0.0),
            reverse=True,
        )

        merged = vector_hits + keyword_hits

        result.reviews = merged[: self._settings.rag_top_k]
        result.vector_hit_count = len(vector_hits)
        result.keyword_hit_count = len(keyword_hits)
        return result
