"""Research Assistant chat UI components (Phase 4.2)."""

from __future__ import annotations

import html
from typing import Any

from pathlib import Path

import streamlit as st

from src.services.dashboard_service import SOURCE_LABELS

_STYLES_DIR = Path(__file__).resolve().parent.parent / "styles"
_PANEL_CSS_PATH = _STYLES_DIR / "research_assistant_panel.css"

SUGGESTED_QUESTIONS: tuple[str, ...] = (
    "Why do users struggle to discover new music?",
    "What causes repetitive listening?",
    "Which user segment faces the biggest discovery challenge?",
    "What recommendation complaints are increasing?",
    "What unmet needs are emerging?",
    "Show evidence supporting these conclusions.",
)

SESSION_MESSAGES_KEY = "research_assistant_messages"
SESSION_PENDING_KEY = "research_assistant_pending"
COMPOSER_CONTAINER_KEY = "ra_chat_composer"
COMPOSER_BOX_KEY = "ra_question_box"
COMPOSER_INPUT_KEY = "ra_question_input"
COMPOSER_FORM_KEY = "ra_question_form"


def init_chat_session() -> None:
    if SESSION_MESSAGES_KEY not in st.session_state:
        st.session_state[SESSION_MESSAGES_KEY] = []


def inject_research_assistant_panel_styles() -> None:
    """Inject panel CSS when the chat opens (survives Streamlit navigation reruns)."""
    if not _PANEL_CSS_PATH.exists():
        return
    css = _PANEL_CSS_PATH.read_text(encoding="utf-8")
    st.markdown(
        f"<!-- sra-ra-panel-styles-v3 -->\n<style>{css}</style>",
        unsafe_allow_html=True,
    )


def queue_question(question: str) -> None:
    st.session_state[SESSION_PENDING_KEY] = question.strip()


def consume_pending_question(chat_input: str | None) -> str | None:
    pending = st.session_state.pop(SESSION_PENDING_KEY, None)
    if pending:
        return pending
    if chat_input and chat_input.strip():
        return chat_input.strip()
    return None


def latest_assistant_message() -> dict[str, Any] | None:
    messages = st.session_state.get(SESSION_MESSAGES_KEY, [])
    for message in reversed(messages):
        if message.get("role") == "assistant" and not message.get("error") and not message.get("info"):
            return message
    return None


def source_label(source: str) -> str:
    return SOURCE_LABELS.get(source, source.replace("_", " ").title())


def render_source_badge(source: str) -> str:
    labels = {
        "playstore": "🟢 Play Store",
        "appstore": "🔵 App Store",
        "reddit": "🟠 Reddit",
    }
    return labels.get(source, source_label(source))


def render_suggested_questions(*, key_prefix: str = "research", show_title: bool = True) -> None:
    if show_title:
        st.markdown('<p class="sra-panel-title">Suggested questions</p>', unsafe_allow_html=True)
    columns = st.columns(2)
    for index, question in enumerate(SUGGESTED_QUESTIONS):
        column = columns[index % 2]
        if column.button(
            question,
            key=f"{key_prefix}_suggested_{index}",
            use_container_width=True,
        ):
            queue_question(question)
            if key_prefix == "ra_popup":
                st.session_state["ra_panel_open"] = True
            st.rerun()


def render_confidence_meter(confidence: float) -> None:
    st.caption(f"Answer confidence: **{confidence:.0%}**")
    st.progress(min(max(confidence, 0.0), 1.0))


def render_response_sections(answer: dict[str, Any]) -> None:
    st.markdown(answer.get("summary", ""))

    themes = answer.get("key_themes") or []
    if themes:
        st.markdown("**Key themes**")
        for theme in themes:
            st.markdown(f"- {theme}")

    root_causes = answer.get("root_causes") or []
    if root_causes:
        st.markdown("**Root causes**")
        for cause in root_causes:
            st.markdown(f"- {cause}")

    segments = answer.get("affected_segments") or []
    if segments:
        st.markdown("**Affected segments**")
        badges = " ".join(
            f'<span class="sra-chip sra-chip-primary">{segment}</span>' for segment in segments
        )
        st.markdown(badges, unsafe_allow_html=True)

    opportunities = answer.get("product_opportunities") or []
    if opportunities:
        st.markdown("**Product opportunities**")
        for opportunity in opportunities:
            st.markdown(f"- {opportunity}")

    confidence = answer.get("confidence")
    if isinstance(confidence, (int, float)):
        render_confidence_meter(float(confidence))


def render_chat_message(message: dict[str, Any]) -> None:
    role = message.get("role", "assistant")
    if role == "user":
        content = html.escape(str(message.get("content", "")))
        _, user_col = st.columns([0.12, 0.88])
        with user_col:
            st.markdown(
                (
                    '<div class="sra-chat-user-bubble">'
                    '<span class="sra-chat-user-chip">You</span>'
                    f"{content}"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
        return

    with st.container(border=True):
        st.markdown(
            (
                '<div class="sra-chat-assistant-header">'
                '<span class="sra-chat-assistant-icon" aria-hidden="true">🎧</span>'
                "<span>AI Research Assistant</span>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

        if message.get("info"):
            st.info(message["info"])
            return

        if message.get("error"):
            st.error(message["error"])
            return

        answer = message.get("answer") or {}
        render_response_sections(answer)

        stats = message.get("retrieval_stats") or {}
        elapsed = message.get("elapsed_seconds")
        caption_parts: list[str] = []
        if isinstance(elapsed, (int, float)):
            caption_parts.append(f"Response time: {elapsed:.1f}s")
        if stats:
            caption_parts.append(
                f"Retrieved {len(answer.get('supporting_evidence') or [])} citations "
                f"from {stats.get('eligible_reviews', '—')} eligible reviews"
            )
        if caption_parts:
            st.caption(" · ".join(caption_parts))


def render_question_composer(*, has_messages: bool) -> str | None:
    """Inline question box rendered inside the panel (not Streamlit's fixed chat_input bar)."""
    title = "Ask a follow-up question" if has_messages else "Ask a question"
    placeholder = (
        "Ask a follow-up question..."
        if has_messages
        else "Ask about Spotify reviews, discovery, or user feedback..."
    )

    with st.container(key=COMPOSER_BOX_KEY, border=False):
        st.markdown(f'<p class="sra-chat-composer-title">{title}</p>', unsafe_allow_html=True)
        with st.form(COMPOSER_FORM_KEY, clear_on_submit=True, border=False):
            question = st.text_input(
                "Question",
                placeholder=placeholder,
                label_visibility="collapsed",
                key=COMPOSER_INPUT_KEY,
            )
            submitted = st.form_submit_button("Send", type="primary", use_container_width=True)

    if submitted and question.strip():
        return question.strip()
    return None


def render_citations_panel(message: dict[str, Any] | None) -> None:
    if not message:
        st.caption("Citations appear here after you ask a question.")
        return

    answer = message.get("answer") or {}
    evidence = answer.get("supporting_evidence") or []
    review_texts = message.get("review_texts") or {}

    if not evidence:
        st.info("No citations in the latest response.")
        return

    st.caption(f"{len(evidence)} cited review(s)")
    for index, item in enumerate(evidence, start=1):
        review_id = str(item.get("review_id", ""))
        source = str(item.get("source", "unknown"))
        rating = item.get("rating")
        rating_text = f"★ {rating}" if rating is not None else "★ n/a"
        excerpt = str(item.get("excerpt", "")).strip()
        full_review = review_texts.get(review_id, {})
        full_text = str(full_review.get("text") or excerpt).strip()
        segment = full_review.get("user_segment")
        header = (
            f"{index}. {render_source_badge(source)} · {rating_text}"
            + (f" · `{segment}`" if segment else "")
        )

        with st.expander(header, expanded=index == 1):
            st.caption(f"Review ID: `{review_id}`")
            st.markdown(f"*Excerpt:* {excerpt}")
            st.markdown("**Full review**")
            st.write(full_text or "Review text unavailable.")
