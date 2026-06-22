"""Floating Research Assistant launcher and bottom-right chat panel (all pages)."""

from __future__ import annotations

import time

import streamlit as st

from app.components.branding import render_section_title
from app.components.research_assistant_ui import (
    SESSION_MESSAGES_KEY,
    consume_pending_question,
    init_chat_session,
    latest_assistant_message,
    render_chat_message,
    render_citations_panel,
    render_suggested_questions,
)
from app.config import get_settings
from src.db.client import check_connection
from src.db.repositories.analysis_repo import AnalysisRepository
from src.llm.errors import LlmQuotaExceededError, format_llm_error, is_quota_exceeded
from src.rag.errors import (
    ResearchAssistantNoCorpusError,
    ResearchAssistantNoDataError,
    ResearchAssistantScopeError,
)
from src.rag.research_assistant import ResearchAssistantResult, ResearchAssistantService

PANEL_OPEN_KEY = "ra_panel_open"
FAB_KEY = "sra_research_fab"
PANEL_KEY = "sra_chat_panel"

def _assistant_message_from_result(
    result: ResearchAssistantResult,
    elapsed_seconds: float,
) -> dict:
    review_texts = {
        str(review.review_id): {
            "text": review.text,
            "source": review.source,
            "rating": review.rating,
            "user_segment": review.user_segment,
        }
        for review in result.retrieval.reviews
    }
    return {
        "role": "assistant",
        "answer": result.answer.model_dump(),
        "review_texts": review_texts,
        "elapsed_seconds": round(elapsed_seconds, 1),
        "retrieval_stats": {
            "vector_hits": result.retrieval.vector_hit_count,
            "keyword_hits": result.retrieval.keyword_hit_count,
            "eligible_reviews": result.retrieval.eligible_review_count,
        },
    }


def _append_info_response(question: str, info_message: str) -> None:
    st.session_state[SESSION_MESSAGES_KEY].append({"role": "user", "content": question})
    st.session_state[SESSION_MESSAGES_KEY].append({"role": "assistant", "info": info_message})


def _append_error_response(question: str, error_message: str) -> None:
    st.session_state[SESSION_MESSAGES_KEY].append({"role": "user", "content": question})
    st.session_state[SESSION_MESSAGES_KEY].append({"role": "assistant", "error": error_message})


def _process_question(question: str) -> None:
    start = time.perf_counter()
    try:
        with st.spinner("Searching evidence and generating answer..."):
            result = ResearchAssistantService().ask(question)
        elapsed = time.perf_counter() - start
        st.session_state[SESSION_MESSAGES_KEY].append({"role": "user", "content": question})
        st.session_state[SESSION_MESSAGES_KEY].append(_assistant_message_from_result(result, elapsed))
    except ResearchAssistantScopeError as exc:
        _append_info_response(question, str(exc))
    except ResearchAssistantNoDataError as exc:
        _append_info_response(question, str(exc))
    except ResearchAssistantNoCorpusError as exc:
        _append_info_response(question, str(exc))
    except LlmQuotaExceededError as exc:
        _append_error_response(
            question,
            f"LLM quota exceeded: {format_llm_error(exc)}. "
            "Try again tomorrow or switch `LLM_PROVIDER` in `.env`.",
        )
    except Exception as exc:
        if is_quota_exceeded(exc):
            _append_error_response(
                question,
                f"LLM quota exceeded: {format_llm_error(exc)}. "
                "Try again tomorrow or switch `LLM_PROVIDER` in `.env`.",
            )
            return

        message = format_llm_error(exc)
        if "Question must not be empty" in message:
            return
        _append_error_response(question, message)


def _render_prerequisites_warning() -> bool:
    settings = get_settings()
    missing = settings.missing_required()
    if missing:
        st.warning(
            "Configure required environment variables before using the Research Assistant: "
            + ", ".join(f"`{key}`" for key in missing)
        )
        return False

    if not check_connection():
        st.error("Cannot connect to Supabase. Check your database configuration.")
        return False

    try:
        eligible_count = len(
            AnalysisRepository().get_rag_eligible_rows(settings.rag_min_confidence)
        )
    except Exception as exc:
        st.error(f"Could not load review evidence: {format_llm_error(exc)}")
        return False

    if eligible_count == 0:
        st.info(
            "No high-confidence analyzed reviews available for RAG yet. "
            "Use **Run Analysis** in the sidebar, then ask your question."
        )
        return False

    st.caption(
        f"{eligible_count} reviews meet the RAG confidence threshold "
        f"(≥ {settings.rag_min_confidence:.0%})."
    )
    return True


def _render_floating_chat_panel() -> None:
    st.markdown('<div class="sra-chat-panel-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    with st.container(key=PANEL_KEY):
        header_left, header_right = st.columns([5, 1])
        with header_left:
            st.markdown("**AI Research Assistant**")
            st.caption(
                "Ask about Spotify reviews — grounded in Play Store, App Store, and Reddit feedback."
            )
        with header_right:
            if st.button("✕", key="ra_panel_close", help="Close chat"):
                st.session_state[PANEL_OPEN_KEY] = False
                st.rerun()

        if not _render_prerequisites_warning():
            return

        render_suggested_questions(key_prefix="ra_popup")
        st.divider()

        for message in st.session_state[SESSION_MESSAGES_KEY]:
            render_chat_message(message)

        prompt = st.chat_input(
            "Ask about Spotify reviews, discovery, or user feedback...",
            key="ra_popup_chat_input",
        )

        question = consume_pending_question(prompt)
        if question:
            _process_question(question)
            st.session_state[PANEL_OPEN_KEY] = True
            st.rerun()

        render_section_title("Citations")
        render_citations_panel(latest_assistant_message())

        if st.button("Clear chat", key="ra_popup_clear", use_container_width=True):
            st.session_state[SESSION_MESSAGES_KEY] = []
            st.session_state[PANEL_OPEN_KEY] = True
            st.rerun()


def render_research_assistant_fab() -> None:
    """Fixed bottom-right Spotify logo button + floating chat panel."""
    init_chat_session()

    if st.button(
        " ",
        key=FAB_KEY,
        help="Your research companion — open AI Research Assistant",
    ):
        st.session_state[PANEL_OPEN_KEY] = not st.session_state.get(PANEL_OPEN_KEY, False)
        st.rerun()

    if st.session_state.get(PANEL_OPEN_KEY):
        _render_floating_chat_panel()
