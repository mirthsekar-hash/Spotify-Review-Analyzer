"""Guardrail tests for Research Assistant scope and relevance."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.rag.errors import ResearchAssistantNoDataError, ResearchAssistantScopeError
from src.rag.guardrails import (
    has_relevant_evidence,
    is_spotify_scope,
    no_data_message,
)
from src.rag.research_assistant import ResearchAssistantService
from src.rag.retriever import RetrievedReview, RetrievalResult


def test_is_spotify_scope_accepts_review_questions():
    assert is_spotify_scope("Why do users struggle to discover new music?")
    assert is_spotify_scope("What recommendation complaints are increasing?")


def test_is_spotify_scope_rejects_off_topic_questions():
    assert not is_spotify_scope("What is the capital of France?")
    assert not is_spotify_scope("How does Netflix recommend movies?")


def test_no_data_message_is_human_friendly():
    message = no_data_message("Why is shuffle broken?")
    assert "Spotify review data" in message
    assert "shuffle broken" in message


def test_has_relevant_evidence_requires_keyword_or_similar_vector_hit():
    review_id = uuid4()
    low_similarity = RetrievalResult(
        question="test",
        reviews=[
            RetrievedReview(
                review_id=review_id,
                source="playstore",
                text="Unrelated",
                rating=3,
                similarity=0.2,
                retrieval_source="vector",
            )
        ],
        vector_hit_count=1,
    )
    assert not has_relevant_evidence(low_similarity, min_similarity=0.45)

    keyword_hit = RetrievalResult(
        question="test",
        reviews=[
            RetrievedReview(
                review_id=review_id,
                source="playstore",
                text="Shuffle repeats songs",
                rating=2,
                retrieval_source="keyword",
            )
        ],
        keyword_hit_count=1,
    )
    assert has_relevant_evidence(keyword_hit, min_similarity=0.45)


def test_service_rejects_out_of_scope_before_llm():
    service = ResearchAssistantService(
        settings=MagicMock(rag_min_similarity=0.45),
        retriever=MagicMock(),
        context_builder=MagicMock(),
    )

    with pytest.raises(ResearchAssistantScopeError):
        service.ask("What is the weather in London?")


def test_service_raises_no_data_when_retrieval_not_relevant():
    retriever = MagicMock()
    retriever.retrieve.return_value = RetrievalResult(
        question="Why is Spotify offline mode broken?",
        reviews=[],
        eligible_review_count=10,
        vector_hit_count=0,
        keyword_hit_count=0,
    )
    service = ResearchAssistantService(
        settings=MagicMock(rag_min_similarity=0.45),
        retriever=retriever,
        context_builder=MagicMock(),
    )

    with pytest.raises(ResearchAssistantNoDataError) as exc_info:
        service.ask("Why is Spotify offline mode broken?")

    assert "Spotify review data" in str(exc_info.value)
