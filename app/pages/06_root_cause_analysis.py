"""Root Cause Analysis dashboard — Phase 3.7."""

from __future__ import annotations

from uuid import UUID

import pandas as pd
import streamlit as st

from app.components.branding import render_page_header, render_section_title
from app.components.evidence_list import render_evidence_list
from app.components.segment_badge import render_segment_badges
from src.services.explorer_service import ExplorerService, RootCauseDetailData, RootCausesExplorerData


@st.cache_data(ttl=30, show_spinner="Loading root causes...")
def load_root_causes(refresh_key: int) -> RootCausesExplorerData:
    return ExplorerService().get_root_causes()


@st.cache_data(ttl=30, show_spinner="Loading root cause evidence...")
def load_root_cause_detail(root_cause_id: str, refresh_key: int) -> RootCauseDetailData:
    return ExplorerService().get_root_cause_detail(UUID(root_cause_id))


def render_empty_state() -> None:
    st.info(
        "No root causes available. Run **Re-run Collective Analysis** after themes "
        "have been generated."
    )


def main() -> None:
    render_page_header(
        "Root Cause Analysis",
        "Underlying systemic causes of discovery failures",
    )

    refresh_key = st.session_state.get("data_version", 0)
    data = load_root_causes(refresh_key)

    if not data.db_connected:
        st.error("Cannot load root causes. Check Supabase connection.")
        return

    if not data.root_causes:
        render_empty_state()
        return

    table_rows = [
        {
            "Rank": index,
            "Root cause": item.root_cause,
            "Frequency": item.frequency,
            "Evidence reviews": item.evidence_count,
            "Affected segments": ", ".join(item.affected_segments) if item.affected_segments else "—",
        }
        for index, item in enumerate(data.root_causes, start=1)
    ]
    render_section_title("Ranked Root Causes")
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    options = {item.root_cause: str(item.id) for item in data.root_causes}
    selected_name = st.selectbox("Evidence panel", options=list(options.keys()))
    selected = next(item for item in data.root_causes if item.root_cause == selected_name)

    st.markdown(f"### {selected.root_cause}")
    st.markdown(f"**Frequency:** {selected.frequency} · **Evidence reviews:** {selected.evidence_count}")
    render_segment_badges(selected.affected_segments, prefix="Affected segments:")

    detail = load_root_cause_detail(options[selected_name], refresh_key)
    render_section_title("Supporting Evidence")
    render_evidence_list(
        detail.reviews,
        empty_message="No evidence reviews linked to this root cause.",
    )


main()
