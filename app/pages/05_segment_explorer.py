"""Segment Explorer dashboard — Phase 3.7."""

from __future__ import annotations

import streamlit as st

from app.components.branding import render_page_header, render_section_title
from app.components.kpi_card import render_kpi_card
from app.components.trust_score_gauge import render_trust_score_gauge
from src.services.explorer_service import ExplorerService, SegmentsExplorerData


@st.cache_data(ttl=30, show_spinner="Loading segments...")
def load_segments(refresh_key: int) -> SegmentsExplorerData:
    return ExplorerService().get_segments()


def render_empty_state() -> None:
    st.info(
        "No segment summaries yet. Run **Re-run Collective Analysis** in the sidebar "
        "after you have analyzed reviews."
    )


def render_segment_cards(data: SegmentsExplorerData) -> None:
    columns = st.columns(2)
    for index, segment in enumerate(data.segments):
        slug = segment.segment_name.lower().replace(" ", "_")
        with columns[index % 2]:
            with st.container(border=True):
                st.markdown(f"#### {segment.segment_name}")
                render_kpi_card("Segment size", segment.size)
                render_trust_score_gauge(
                    segment.recommendation_trust_score,
                    key=f"segment_gauge_overview_{slug}",
                )


def render_segment_detail(data: SegmentsExplorerData) -> None:
    segment_names = [segment.segment_name for segment in data.segments]
    selected = st.selectbox("Segment detail view", options=segment_names)
    segment = next(item for item in data.segments if item.segment_name == selected)

    st.markdown(f"### {segment.segment_name}")
    detail_cols = st.columns(2)
    with detail_cols[0]:
        st.markdown("**Listening goals**")
        if segment.listening_goals:
            for goal in segment.listening_goals:
                st.markdown(f"- {goal}")
        else:
            st.caption("No goals recorded.")

        st.markdown("**Discovery behavior**")
        if segment.discovery_behavior:
            for behavior in segment.discovery_behavior:
                st.markdown(f"- {behavior}")
        else:
            st.caption("No behaviors recorded.")

    with detail_cols[1]:
        st.markdown("**Top frustrations**")
        if segment.top_frustrations:
            for frustration in segment.top_frustrations:
                st.markdown(f"- {frustration}")
        else:
            st.caption("No frustrations recorded.")
        render_trust_score_gauge(
            segment.recommendation_trust_score,
            key=f"segment_gauge_detail_{selected.replace(' ', '_').lower()}",
        )


def main() -> None:
    render_page_header(
        "Segment Explorer",
        "Compare listener segments, trust scores, and discovery profiles",
    )

    refresh_key = st.session_state.get("data_version", 0)
    data = load_segments(refresh_key)

    if not data.db_connected:
        st.error("Cannot load segments. Check Supabase connection.")
        return

    if not data.segments:
        render_empty_state()
        return

    render_section_title("Segment Overview")
    render_segment_cards(data)
    render_section_title("Segment Detail")
    render_segment_detail(data)


main()
