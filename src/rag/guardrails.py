"""Research Assistant guardrails and user-facing messages."""

from __future__ import annotations

import re

from src.rag.retriever import RetrievalResult

OUT_OF_SCOPE_MESSAGE = (
    "I'm here to help with **Spotify user feedback and review insights** only. "
    "Your question doesn't look related to Spotify or the reviews in this dataset.\n\n"
    "Try asking about music discovery, recommendations, playlists, shuffle, user segments, "
    "complaints, themes, or root causes drawn from our ingested reviews."
)

NO_CORPUS_MESSAGE = (
    "There aren't any analyzed Spotify reviews ready to search yet. "
    "Use **Run Analysis** in the sidebar first, then come back to ask your question."
)


def no_data_message(question: str) -> str:
    """Human-friendly message when the corpus has no relevant evidence for the question."""
    trimmed = question.strip().rstrip("?.!")
    return (
        f"I couldn't find any Spotify review data that speaks to your question about "
        f"**{trimmed}**.\n\n"
        "That usually means this topic isn't covered in the reviews we've ingested and analyzed so far. "
        "You could try rephrasing your question, pick one of the suggested questions above, "
        "or ingest more reviews from the sidebar."
    )


_OFF_TOPIC_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(netflix|hulu|disney\+?|youtube music|apple music|amazon music|tidal|deezer)\b",
        r"\b(weather|recipe|cooking|football|basketball|election|politics|stock market|crypto)\b",
        r"\b(write (me )?(a )?(python|javascript|java) (code|script)|debug my code)\b",
        r"\b(capital of|who won the|translate .+ to)\b",
    )
)

_IN_SCOPE_SIGNALS: tuple[str, ...] = (
    "spotify",
    "music",
    "playlist",
    "discover",
    "discovery",
    "recommend",
    "shuffle",
    "listening",
    "listen",
    "review",
    "reviews",
    "feedback",
    "user",
    "users",
    "segment",
    "segments",
    "theme",
    "themes",
    "complaint",
    "complaints",
    "app store",
    "play store",
    "reddit",
    "algorithm",
    "premium",
    "podcast",
    "artist",
    "song",
    "songs",
    "track",
    "tracks",
    "radio",
    "unmet need",
    "unmet needs",
    "root cause",
    "root causes",
    "evidence",
    "frustration",
    "frustrations",
    "explorer",
    "repetitive",
    "stale",
    "filter bubble",
)


def is_spotify_scope(question: str) -> bool:
    """Return True when the question is plausibly about Spotify review research."""
    cleaned = question.strip()
    if not cleaned:
        return False

    lower = cleaned.lower()
    if any(pattern.search(lower) for pattern in _OFF_TOPIC_PATTERNS):
        return False

    return any(signal in lower for signal in _IN_SCOPE_SIGNALS)


def has_relevant_evidence(retrieval: RetrievalResult, min_similarity: float) -> bool:
    """Return True when retrieval found evidence tied to the question."""
    if retrieval.keyword_hit_count > 0:
        return True

    vector_reviews = [
        review for review in retrieval.reviews if review.retrieval_source == "vector"
    ]
    if not vector_reviews:
        return False

    best_similarity = max((review.similarity or 0.0) for review in vector_reviews)
    return best_similarity >= min_similarity
