"""Segment priority ranking panel for Executive Summary."""

from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from src.services.dashboard_service import SegmentPriorityData


def render_segment_priority_panel(data: SegmentPriorityData) -> None:
    if not data.db_connected:
        return

    if data.total_analyzed == 0:
        st.info(
            "Segment priority will appear after reviews are analyzed. "
            "Click **Run Analysis** in the sidebar."
        )
        return

    if not data.items:
        st.info(
            "No user segments found in analyzed reviews yet. "
            "Run **Run Analysis**, then **Re-run Collective Analysis**."
        )
        return

    recommended = next((item for item in data.items if item.is_recommended), None)
    if recommended:
        sample_note = (
            " <span class='sra-priority-warning'>(small sample — interpret with caution)</span>"
            if recommended.low_sample
            else ""
        )
        frustration_html = ""
        if recommended.top_frustration:
            frustration_html = (
                f"<p class='sra-priority-frustration'>"
                f"Top frustration: {html.escape(recommended.top_frustration)}</p>"
            )

        st.markdown(
            f"""
            <div class="sra-segment-priority-callout">
              <p class="sra-priority-label">Recommended focus segment</p>
              <p class="sra-priority-name">{html.escape(recommended.segment_name)}{sample_note}</p>
              <p class="sra-priority-metrics">
                Priority score {recommended.priority_score:.0f} ·
                {recommended.size} reviews ({recommended.pct_of_analyzed}% of sample) ·
                {recommended.negative_pct}% negative ·
                {recommended.rec_complaint_pct}% rec complaints
              </p>
              {frustration_html}
            </div>
            """,
            unsafe_allow_html=True,
        )
        if data.recommended_rationale:
            st.caption(data.recommended_rationale)

    rows = [
        {
            "Rank": item.rank,
            "Segment": item.segment_name + (" ★" if item.is_recommended else ""),
            "Reviews": item.size,
            "% Sample": f"{item.pct_of_analyzed:.1f}%",
            "Negative %": f"{item.negative_pct:.1f}%",
            "Rec Complaint %": f"{item.rec_complaint_pct:.1f}%",
            "Priority Score": f"{item.priority_score:.0f}",
            "Trust": (
                f"{item.trust_score:.0f}"
                if item.trust_score is not None
                else "—"
            ),
        }
        for item in data.items
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption(
        "Priority score = review count × (negative % + rec-complaint %). "
        "Higher scores indicate segments with both scale and discovery pain."
    )
