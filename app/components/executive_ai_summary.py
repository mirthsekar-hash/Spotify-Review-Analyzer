"""Executive AI summary panel for the dashboard."""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.schemas.executive_summary import ExecutiveSummaryOutput, format_executive_summary_markdown


def render_executive_ai_summary_from_cache(cached: dict[str, Any] | None) -> None:
    if not cached:
        st.info(
            "Run **Re-run Collective Analysis** in the sidebar to generate an AI executive summary "
            "from themes, segments, and review evidence."
        )
        return

    if not cached.get("available", True):
        st.info(
            cached.get("reason")
            or "Collective insights are not ready yet. Run collective analysis first."
        )
        return

    output_data = cached.get("output")
    if not output_data:
        st.info("AI executive summary is not available yet.")
        return

    output = ExecutiveSummaryOutput.model_validate(output_data)
    with st.container(border=True):
        st.markdown(
            '<p class="sra-panel-title" style="margin-top:0;">AI-generated summary</p>',
            unsafe_allow_html=True,
        )
        st.markdown(format_executive_summary_markdown(output))
    st.caption(
        "Grounded in "
        f"{cached.get('theme_count', 0)} themes, "
        f"{cached.get('segment_count', 0)} segments, "
        f"{cached.get('root_cause_count', 0)} root causes, and "
        f"{cached.get('unmet_need_count', 0)} unmet needs."
    )
