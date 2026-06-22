"""Sidebar analysis handlers."""

from __future__ import annotations

import logging
import traceback

import streamlit as st

from app.config import clear_settings_cache, get_settings
from src.analysis.analysis_pipeline import AnalysisPipeline
from src.db.client import check_connection, clear_supabase_client_cache

logger = logging.getLogger(__name__)


def handle_run_analysis(limit: int | None = None) -> None:
    if not check_connection():
        st.sidebar.error("Supabase not connected. Run the migration first.")
        return

    try:
        clear_settings_cache()
        clear_supabase_client_cache()
        settings = get_settings()

        with st.spinner("Running AI analysis and embeddings..."):
            result = AnalysisPipeline(settings=settings).run(limit=limit)

        analyzed = result.analysis.analyzed
        embedded = result.embeddings.embedded
        failed = result.analysis.failed + result.embeddings.failed
        skipped = result.analysis.skipped

        if analyzed or embedded:
            limit_note = f" (limit {limit})" if limit else ""
            st.sidebar.success(
                f"Analyzed {analyzed} reviews, embedded {embedded} "
                f"({failed} failed, {skipped} skipped){limit_note}"
            )
        elif result.analysis.quota_exceeded:
            st.sidebar.error("LLM API quota exceeded — analysis stopped early.")
            st.sidebar.caption(result.analysis.quota_message or "Check your LLM API quota or try again later.")
            st.sidebar.caption(
                "If using Groq free tier, daily limits vary by model. "
                "Reduce 'Max reviews to analyze' or wait for quota reset."
            )
        elif failed:
            st.sidebar.error(
                f"Analysis failed for all {result.reviews_fetched} reviews. "
                "Check LLM_PROVIDER and API keys in .env."
            )
        else:
            st.sidebar.info("No unanalyzed reviews found.")

        st.session_state["last_analysis"] = {
            "fetched": result.reviews_fetched,
            "analyzed": analyzed,
            "embedded": embedded,
            "failed": failed,
        }
        st.session_state["data_version"] = st.session_state.get("data_version", 0) + 1
    except Exception as exc:
        logger.exception("Analysis pipeline failed")
        st.sidebar.error(f"Analysis failed: {exc}")
        with st.sidebar.expander("Error details"):
            st.code(traceback.format_exc())
