"""Research assistant service tests with mocked retrieval and LLM."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.rag.context_builder import RagContext
from src.rag.errors import ResearchAssistantNoCorpusError
from src.rag.research_assistant import ResearchAssistantService
from src.rag.retriever import RetrievedReview, RetrievalResult
from src.schemas.research_assistant import ResearchAssistantOutput


def _retrieval(review_id):
    return RetrievalResult(
        question="Why do users repeat playlists?",
        reviews=[
            RetrievedReview(
                review_id=review_id,
                source="playstore",
                text="I keep hearing the same songs on shuffle.",
                rating=2,
                similarity=0.9,
                sentiment="negative",
                primary_problem="Shuffle repetition",
                discovery_challenge="Lack of variety",
                user_segment="Playlist-Dependent Listener",
                confidence_score=0.9,
            )
        ],
        vector_hit_count=1,
        eligible_review_count=1,
    )


@patch("src.rag.research_assistant.structured_completion")
def test_research_assistant_validates_and_sanitizes_evidence(mock_completion):
    review_id = uuid4()
    retrieval = _retrieval(review_id)
    context = RagContext(
        question=retrieval.question,
        reviews_block="review context",
        retrieved_review_ids=[review_id],
        token_estimate=100,
    )

    mock_completion.return_value = ResearchAssistantOutput.model_validate(
        {
            "summary": "Users experience repetitive shuffle behavior.",
            "key_themes": ["Shuffle repetition"],
            "root_causes": ["Limited pool rotation"],
            "affected_segments": ["Playlist-Dependent Listener"],
            "supporting_evidence": [
                {
                    "review_id": str(review_id),
                    "excerpt": "I keep hearing the same songs on shuffle.",
                    "source": "playstore",
                    "rating": 2,
                },
                {
                    "review_id": str(uuid4()),
                    "excerpt": "Hallucinated quote.",
                    "source": "reddit",
                    "rating": 1,
                },
            ],
            "product_opportunities": ["Improve shuffle diversity"],
            "confidence": 0.8,
        }
    )

    retriever = MagicMock()
    retriever.retrieve.return_value = retrieval
    context_builder = MagicMock()
    context_builder.build.return_value = context
    context_builder.build_user_content.return_value = "user content"

    service = ResearchAssistantService(
        settings=MagicMock(rag_min_similarity=0.45),
        retriever=retriever,
        context_builder=context_builder,
    )
    result = service.ask("Why do users repeat playlists?")

    assert result.answer.summary.startswith("Users experience")
    assert len(result.answer.supporting_evidence) == 1
    assert result.answer.supporting_evidence[0].review_id == str(review_id)
    assert len(result.dropped_evidence_ids) == 1
    mock_completion.assert_called_once()


@patch("src.rag.research_assistant.structured_completion")
def test_research_assistant_raises_when_no_corpus(mock_completion):
    retriever = MagicMock()
    retriever.retrieve.return_value = RetrievalResult(
        question="Why do users struggle with Spotify playlists?",
        reviews=[],
        eligible_review_count=0,
    )
    service = ResearchAssistantService(
        settings=MagicMock(rag_min_similarity=0.45),
        retriever=retriever,
        context_builder=MagicMock(),
    )

    with pytest.raises(ResearchAssistantNoCorpusError):
        service.ask("Why do users struggle with Spotify playlists?")

    mock_completion.assert_not_called()
