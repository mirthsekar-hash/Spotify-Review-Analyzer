"""RAG Research Assistant service."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from uuid import UUID

from app.config import Settings, get_settings
from src.analysis.prompts import load_prompt
from src.llm.structured import structured_completion
from src.rag.context_builder import ContextBuilder, RagContext
from src.rag.errors import (
    ResearchAssistantNoCorpusError,
    ResearchAssistantNoDataError,
    ResearchAssistantScopeError,
)
from src.rag.guardrails import (
    NO_CORPUS_MESSAGE,
    OUT_OF_SCOPE_MESSAGE,
    has_relevant_evidence,
    is_spotify_scope,
    no_data_message,
)
from src.rag.retriever import Retriever, RetrievalResult
from src.schemas.research_assistant import ResearchAssistantOutput, SupportingEvidence

logger = logging.getLogger(__name__)


@dataclass
class ResearchAssistantResult:
    question: str
    answer: ResearchAssistantOutput
    retrieval: RetrievalResult
    context: RagContext
    filtered_evidence_count: int = 0
    dropped_evidence_ids: list[str] = field(default_factory=list)


class ResearchAssistantService:
    def __init__(
        self,
        settings: Settings | None = None,
        retriever: Retriever | None = None,
        context_builder: ContextBuilder | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._retriever = retriever or Retriever(self._settings)
        self._context_builder = context_builder or ContextBuilder()
        self._system_prompt = load_prompt("research_assistant.txt")

    def _sanitize_evidence(
        self,
        output: ResearchAssistantOutput,
        allowed_review_ids: set[str],
        question: str,
    ) -> tuple[ResearchAssistantOutput, list[str]]:
        kept: list[SupportingEvidence] = []
        dropped: list[str] = []

        for item in output.supporting_evidence:
            if item.review_id in allowed_review_ids:
                kept.append(item)
            else:
                dropped.append(item.review_id)
                logger.warning("Dropped hallucinated review_id from LLM output: %s", item.review_id)

        if not kept and output.supporting_evidence:
            raise ResearchAssistantNoDataError(no_data_message(question))

        if kept != output.supporting_evidence:
            output = output.model_copy(update={"supporting_evidence": kept})
        return output, dropped

    def ask(self, question: str) -> ResearchAssistantResult:
        cleaned_question = question.strip()
        if not cleaned_question:
            raise ValueError("Question must not be empty")

        if not is_spotify_scope(cleaned_question):
            raise ResearchAssistantScopeError(OUT_OF_SCOPE_MESSAGE)

        retrieval = self._retriever.retrieve(cleaned_question)

        if retrieval.eligible_review_count == 0:
            raise ResearchAssistantNoCorpusError(NO_CORPUS_MESSAGE)

        if not has_relevant_evidence(retrieval, self._settings.rag_min_similarity):
            raise ResearchAssistantNoDataError(no_data_message(cleaned_question))

        context = self._context_builder.build(retrieval)
        user_content = self._context_builder.build_user_content(context)

        raw_output = structured_completion(
            system_prompt=self._system_prompt,
            user_content=user_content,
            schema_model=ResearchAssistantOutput,
        )
        if not isinstance(raw_output, ResearchAssistantOutput):
            raise TypeError("structured_completion returned unexpected type")

        allowed_ids = {str(review_id) for review_id in context.retrieved_review_ids}
        answer, dropped = self._sanitize_evidence(raw_output, allowed_ids, cleaned_question)

        return ResearchAssistantResult(
            question=cleaned_question,
            answer=answer,
            retrieval=retrieval,
            context=context,
            filtered_evidence_count=len(answer.supporting_evidence),
            dropped_evidence_ids=dropped,
        )

    @staticmethod
    def allowed_review_ids(context: RagContext) -> set[UUID]:
        return set(context.retrieved_review_ids)
