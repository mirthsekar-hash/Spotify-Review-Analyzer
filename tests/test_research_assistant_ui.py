"""Tests for Research Assistant UI helpers."""

from app.components.research_assistant_ui import (
    SESSION_MESSAGES_KEY,
    SESSION_PENDING_KEY,
    consume_pending_question,
    latest_assistant_message,
    source_label,
)


def test_source_label_maps_known_sources():
    assert source_label("playstore") == "Play Store"
    assert source_label("reddit") == "Reddit"


def test_consume_pending_question_prefers_pending():
    import streamlit as st

    st.session_state[SESSION_PENDING_KEY] = "Why do users repeat playlists?"
    assert consume_pending_question(None) == "Why do users repeat playlists?"
    assert SESSION_PENDING_KEY not in st.session_state

    st.session_state[SESSION_PENDING_KEY] = "First"
    assert consume_pending_question("Second") == "First"


def test_latest_assistant_message_skips_errors():
    import streamlit as st

    st.session_state[SESSION_MESSAGES_KEY] = [
        {"role": "user", "content": "Q"},
        {"role": "assistant", "error": "failed"},
        {
            "role": "assistant",
            "answer": {"summary": "Answer", "supporting_evidence": []},
        },
    ]
    latest = latest_assistant_message()
    assert latest is not None
    assert latest["answer"]["summary"] == "Answer"
