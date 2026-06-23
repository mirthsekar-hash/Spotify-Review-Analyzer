"""Source Analysis dashboard — Phase 2.4."""

from __future__ import annotations

import streamlit as st

from app.components.branding import render_page_header, render_section_title
from app.components.sentiment_chart import (
    render_review_count_by_source,
    render_sentiment_by_source_chart,
)
from app.components.source_comparison_table import render_source_comparison_table
from src.services.dashboard_service import SOURCE_LABELS, DashboardService, SourceAnalysisData


@st.cache_data(ttl=30, show_spinner="Loading source analysis...")
def load_source_analysis(refresh_key: int) -> SourceAnalysisData:
    return DashboardService().get_source_analysis()


def render_empty_state() -> None:
    st.info(
        "No reviews in the database yet. Use the sidebar to **Fetch Latest Reviews**, "
        "then click **Run Analysis**."
    )


def render_partial_analysis_banner(data: SourceAnalysisData) -> None:
    if data.total_reviews == 0:
        return
    if data.total_analyzed < data.total_reviews:
        pending = data.total_reviews - data.total_analyzed
        st.warning(
            f"**{data.total_analyzed} of {data.total_reviews}** reviews analyzed. "
            f"Run **Run Analysis** in the sidebar to process the remaining {pending}."
        )


def render_top_complaints(data: SourceAnalysisData) -> None:
    render_section_title("Top Complaints by Source")
    columns = st.columns(3)

    for column, source in zip(columns, data.sources.keys(), strict=True):
        metrics = data.sources[source]
        with column:
            st.markdown(f"**{SOURCE_LABELS.get(source, source)}**")
            if not metrics.top_complaints:
                st.caption("No analyzed complaints yet.")
                continue
            for rank, (complaint, count) in enumerate(metrics.top_complaints, start=1):
                st.markdown(f"{rank}. {complaint} ({count})")


def main() -> None:
    render_page_header(
        "Source Analysis",
        "Compare Play Store, App Store, and Reddit feedback side by side",
    )

    refresh_key = st.session_state.get("data_version", 0)
    data = load_source_analysis(refresh_key)

    if not data.db_connected:
        st.error("Cannot load source analysis. Check Supabase connection and migration.")
        return

    if data.total_reviews == 0:
        render_empty_state()
        return

    render_partial_analysis_banner(data)

    count_col, sentiment_col = st.columns(2)
    with count_col:
        render_section_title("Review Count by Source")
        render_review_count_by_source(data.sources)
    with sentiment_col:
        render_section_title("Sentiment by Source")
        render_sentiment_by_source_chart(data.sources)

    render_section_title("Source Comparison")
    render_source_comparison_table(data)

    render_top_complaints(data)


main()
