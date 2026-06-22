"""Streamlit application entry point and global sidebar."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.components.analysis_handlers import handle_run_analysis
from app.components.branding import (
    APP_NAME,
    inject_global_theme,
    render_sidebar_branding,
    render_sidebar_page_links,
)
from app.components.ingestion_handlers import (
    handle_all_stores_fetch,
    handle_appstore_fetch,
    handle_csv_upload,
    handle_playstore_fetch,
    handle_reddit_fetch,
)
from app.components.pipeline_handlers import (
    handle_fetch_latest_reviews,
    handle_rerun_collective_analysis,
    render_pipeline_status_panel,
)
from app.components.research_assistant_popup import render_research_assistant_fab
from app.config import get_settings
from src.db.client import check_connection
from src.db.repositories.reviews_repo import ReviewsRepository

APP_DIR = Path(__file__).parent
PAGES_DIR = APP_DIR / "pages"


def render_sidebar() -> None:
    settings = get_settings()
    missing = settings.missing_required()

    st.sidebar.markdown("---")
    st.sidebar.subheader("Pipeline Actions")

    fetch_latest_clicked = st.sidebar.button(
        "Fetch Latest Reviews",
        type="primary",
        use_container_width=True,
        help="Parallel ingest from Play Store, App Store, and Reddit, then analyze new reviews",
    )

    fetch_playstore_clicked = st.sidebar.button(
        "Fetch Play Store Reviews",
        use_container_width=True,
        help="Scrape Google Play Store reviews for Spotify",
    )
    fetch_appstore_clicked = st.sidebar.button(
        "Fetch App Store Reviews",
        use_container_width=True,
        help="Live scrape Apple App Store reviews for Spotify",
    )
    fetch_all_clicked = st.sidebar.button(
        "Fetch All Store Reviews",
        use_container_width=True,
        help="Parallel Play + App Store scrape into Supabase (logged in pipeline_runs; 5–15 min)",
    )
    fetch_reddit_clicked = st.sidebar.button(
        "Fetch Reddit Discussions",
        use_container_width=True,
        help="Scrape Spotify-related Reddit posts and comments (falls back to CSV on rate limit)",
    )
    uploaded_csv = st.sidebar.file_uploader(
        "Import CSV (Fallback)",
        type=["csv"],
        help="Upload CSV with source, text, rating columns",
    )

    if fetch_latest_clicked:
        handle_fetch_latest_reviews()

    if fetch_playstore_clicked:
        handle_playstore_fetch()

    if fetch_appstore_clicked:
        handle_appstore_fetch()

    if fetch_all_clicked:
        handle_all_stores_fetch()

    if fetch_reddit_clicked:
        handle_reddit_fetch()

    if uploaded_csv is not None:
        handle_csv_upload(uploaded_csv)

    analysis_limit = st.sidebar.number_input(
        "Max reviews to analyze",
        min_value=0,
        value=15,
        step=1,
        help="Cap how many unanalyzed reviews to process this run. Use 0 for no limit.",
    )

    analyze_clicked = st.sidebar.button(
        "Run Analysis",
        use_container_width=True,
        help="Analyze unanalyzed reviews with the configured LLM (Groq) and Gemini embeddings",
    )
    collective_clicked = st.sidebar.button(
        "Re-run Collective Analysis",
        use_container_width=True,
        help="Re-run theme extraction, segmentation, root cause, and unmet need engines",
    )
    if analyze_clicked:
        limit = int(analysis_limit) if analysis_limit > 0 else None
        handle_run_analysis(limit=limit)

    if collective_clicked:
        handle_rerun_collective_analysis()

    st.sidebar.markdown("---")
    st.sidebar.subheader("Pipeline Status")
    render_pipeline_status_panel()

    last_run = st.session_state.get("last_ingestion")
    last_analysis = st.session_state.get("last_analysis")
    if last_run:
        st.sidebar.markdown("**Last manual ingestion**")
        st.sidebar.markdown(f"- Source: {last_run.get('source', 'unknown')}")
        st.sidebar.markdown(f"- Stored: {last_run.get('stored', 0)}")

    if last_analysis:
        st.sidebar.markdown(
            f"**Last analysis:** {last_analysis.get('analyzed', 0)} analyzed, "
            f"{last_analysis.get('embedded', 0)} embedded"
        )

    if check_connection():
        try:
            counts = ReviewsRepository().count_by_source()
            total = sum(counts.values())
            st.sidebar.markdown(f"**Total in DB:** {total}")
            st.sidebar.caption(
                f"Play: {counts.get('playstore', 0)} | "
                f"App: {counts.get('appstore', 0)} | "
                f"Reddit: {counts.get('reddit', 0)}"
            )
        except Exception:
            pass

    st.sidebar.markdown("---")
    st.sidebar.subheader("Database")

    if missing:
        st.sidebar.warning("Database check skipped — configure Supabase first.")
    elif check_connection():
        st.sidebar.success("Supabase connected")
    else:
        st.sidebar.error("Supabase unreachable or migration not applied")
        st.sidebar.caption("Run `supabase/migrations/001_initial_schema.sql` in the SQL Editor.")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Configuration")

    if missing:
        st.sidebar.error("Missing required environment variables:")
        for key in missing:
            st.sidebar.markdown(f"- `{key}`")
        st.sidebar.caption(
            "Local: update `.env` and restart. "
            "Streamlit Cloud: **Manage app → Secrets** (TOML), then reboot the app."
        )
    else:
        st.sidebar.success("Configuration loaded")
        st.sidebar.markdown(f"- LLM: `{settings.llm_provider}` / `{settings.active_llm_model()}`")
        st.sidebar.markdown(
            f"- Embeddings: `{settings.embedding_provider}` / "
            f"`{settings.gemini_embedding_model if settings.embedding_provider == 'gemini' else settings.openai_embedding_model}`"
        )


def _page_path(filename: str) -> str:
    return str(PAGES_DIR / filename)


def _build_pages() -> list:
    return [
        st.Page(_page_path("01_executive_summary.py"), title="Executive Summary", icon="📊"),
        st.Page(_page_path("02_source_analysis.py"), title="Source Analysis", icon="📁"),
        st.Page(_page_path("11_review_discovery.py"), title="Review Discovery", icon="🔎"),
        st.Page(_page_path("03_discovery_challenges.py"), title="Discovery Challenges", icon="🔍"),
        st.Page(_page_path("04_theme_explorer.py"), title="Theme Explorer", icon="🏷️"),
        st.Page(_page_path("05_segment_explorer.py"), title="Segment Explorer", icon="👥"),
        st.Page(_page_path("06_root_cause_analysis.py"), title="Root Cause Analysis", icon="🎯"),
        st.Page(_page_path("07_unmet_needs.py"), title="Unmet Needs", icon="💡"),
        st.Page(_page_path("08_discovery_journey.py"), title="Discovery Journey", icon="🗺️"),
        st.Page(_page_path("09_interview_validation.py"), title="Interview Validation", icon="✅"),
    ]


def main() -> None:
    from src.deploy.secrets import bootstrap_settings

    bootstrap_settings()

    st.set_page_config(
        page_title=APP_NAME,
        page_icon="🎧",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    inject_global_theme()

    pages = _build_pages()
    navigation = st.navigation(pages, position="hidden")

    render_sidebar_branding()
    render_sidebar_page_links(pages)
    render_sidebar()
    render_research_assistant_fab()

    navigation.run()


if __name__ == "__main__":
    main()
