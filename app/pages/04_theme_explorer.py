"""Theme Explorer dashboard — Phase 3.7."""

from __future__ import annotations

from uuid import UUID

import streamlit as st

from app.components.branding import render_page_header, render_section_title
from app.components.evidence_list import render_evidence_list
from app.components.segment_badge import render_segment_badges
from app.components.sentiment_chart import render_segment_distribution_chart
from src.services.explorer_service import ExplorerService, ThemeDetailData, ThemesExplorerData


@st.cache_data(ttl=30, show_spinner="Loading themes...")
def load_themes(refresh_key: int) -> ThemesExplorerData:
    return ExplorerService().get_themes()


@st.cache_data(ttl=30, show_spinner="Loading theme detail...")
def load_theme_detail(theme_id: str, refresh_key: int) -> ThemeDetailData:
    return ExplorerService().get_theme_detail(UUID(theme_id))


def render_empty_state() -> None:
    st.info(
        "No themes available. Run **Re-run Collective Analysis** in the sidebar "
        "after ingesting and analyzing reviews."
    )


def render_related_insights(detail: ThemeDetailData) -> None:
    render_section_title("Related Insights")
    col_rc, col_un = st.columns(2)

    with col_rc:
        st.markdown("**Related root causes**")
        if detail.related_root_causes:
            for item in detail.related_root_causes[:5]:
                segments = ", ".join(item.affected_segments) if item.affected_segments else "—"
                st.markdown(f"- **{item.root_cause}** (freq {item.frequency}, {segments})")
        else:
            st.caption("No overlapping root causes by segment.")

    with col_un:
        st.markdown("**Related unmet needs**")
        st.caption("Top opportunities from collective analysis.")
        if detail.related_unmet_needs:
            for item in detail.related_unmet_needs[:5]:
                score = f"{item.opportunity_score:.0f}" if item.opportunity_score is not None else "—"
                st.markdown(f"- **{item.need}** (opportunity {score})")
        else:
            st.caption("No overlapping unmet needs by segment.")


def main() -> None:
    render_page_header(
        "Theme Explorer",
        "Drill into collective themes, supporting reviews, and related insights",
    )

    refresh_key = st.session_state.get("data_version", 0)
    data = load_themes(refresh_key)

    if not data.db_connected:
        st.error("Cannot load themes. Check Supabase connection.")
        return

    if not data.themes:
        render_empty_state()
        return

    themes_by_frequency = sorted(data.themes, key=lambda item: (-item.frequency, item.theme_name))
    theme_options = {item.theme_name: str(item.id) for item in themes_by_frequency}
    selected_name = st.selectbox(
        "Select theme",
        options=list(theme_options.keys()),
        help="Themes sorted by frequency (highest first)",
    )
    selected_id = theme_options[selected_name]
    selected_summary = next(item for item in data.themes if str(item.id) == selected_id)

    st.markdown(f"### {selected_name}")
    metric_cols = st.columns(4)
    metric_cols[0].metric("Frequency", selected_summary.frequency)
    metric_cols[1].metric(
        "Impact score",
        f"{selected_summary.impact_score:.0f}" if selected_summary.impact_score is not None else "—",
    )
    metric_cols[2].metric("Evidence reviews", selected_summary.review_count)
    metric_cols[3].metric("Segments", len(selected_summary.affected_segments))
    render_segment_badges(selected_summary.affected_segments, prefix="Affected segments:")

    detail = load_theme_detail(selected_id, refresh_key)
    if not detail.theme:
        st.warning("Theme detail could not be loaded.")
        return

    chart_col, evidence_col = st.columns([1, 1.2])
    with chart_col:
        render_section_title("Segment Distribution")
        render_segment_distribution_chart(detail.segment_counts)
    with evidence_col:
        render_section_title("Supporting Reviews")
        render_evidence_list(
            detail.reviews,
            empty_message="No linked reviews found for this theme.",
        )

    render_related_insights(detail)


main()
