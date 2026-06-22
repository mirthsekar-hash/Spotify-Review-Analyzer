"""Discovery Challenges dashboard — theme-powered (Phase 3.7)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.components.branding import render_page_header, render_section_title
from app.components.segment_badge import render_impact_badge, render_segment_badges
from src.services.dashboard_service import DashboardService, DiscoveryChallengesData
from src.services.explorer_service import ExplorerService, ThemesExplorerData


@st.cache_data(ttl=30, show_spinner="Loading discovery themes...")
def load_themes(refresh_key: int) -> ThemesExplorerData:
    return ExplorerService().get_themes()


@st.cache_data(ttl=30, show_spinner="Loading discovery challenges...")
def load_interim_challenges(refresh_key: int) -> DiscoveryChallengesData:
    return DashboardService().get_top_discovery_challenges(limit=10)


def render_empty_state() -> None:
    st.info(
        "No theme data yet. Run **Re-run Collective Analysis** in the sidebar after "
        "you have at least 50 analyzed reviews."
    )


def render_theme_table(data: ThemesExplorerData) -> None:
    table_rows = [
        {
            "Rank": index,
            "Theme": item.theme_name,
            "Frequency": item.frequency,
            "Impact": f"{item.impact_score:.0f}" if item.impact_score is not None else "—",
            "Reviews": item.review_count,
            "Affected segments": ", ".join(item.affected_segments) if item.affected_segments else "—",
        }
        for index, item in enumerate(data.themes, start=1)
    ]
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    render_section_title("Impact Highlights")
    for item in data.themes[:5]:
        with st.container(border=True):
            st.markdown(f"**{item.theme_name}**")
            col_a, col_b = st.columns([1, 2])
            with col_a:
                render_impact_badge(item.impact_score)
                st.caption(f"Frequency: {item.frequency} · Evidence reviews: {item.review_count}")
            with col_b:
                render_segment_badges(item.affected_segments, prefix="Segments:")


def render_interim_fallback(data: DiscoveryChallengesData) -> None:
    st.warning(
        "Collective themes are not available yet. Showing interim per-review "
        "`discovery_challenge` aggregations instead."
    )
    table_rows = [
        {
            "Rank": index,
            "Discovery challenge": item.challenge,
            "Frequency": item.frequency,
            "Negative %": f"{item.negative_pct:.1f}%",
            "Affected segments": ", ".join(item.affected_segments) if item.affected_segments else "—",
        }
        for index, item in enumerate(data.challenges, start=1)
    ]
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
    st.caption(f"Based on {data.total_analyzed} analyzed reviews.")


def main() -> None:
    render_page_header(
        "Discovery Challenges",
        "Discovery themes ranked by collective impact score",
    )

    refresh_key = st.session_state.get("data_version", 0)
    theme_data = load_themes(refresh_key)

    if not theme_data.db_connected:
        st.error("Cannot load discovery challenges. Check Supabase connection.")
        return

    if theme_data.themes:
        render_section_title("Themes by Impact Score")
        render_theme_table(theme_data)
        st.caption(
            f"{len(theme_data.themes)} themes from collective analysis. "
            "Open **Theme Explorer** for drill-down."
        )
        return

    interim = load_interim_challenges(refresh_key)
    if interim.challenges:
        render_interim_fallback(interim)
        return

    render_empty_state()


main()
