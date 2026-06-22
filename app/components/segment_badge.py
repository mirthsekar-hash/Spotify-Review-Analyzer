"""Segment label badges for explorer dashboards."""

from __future__ import annotations

import streamlit as st


def render_segment_badges(segments: list[str], *, prefix: str = "") -> None:
    if not segments:
        st.caption("No segments identified.")
        return

    label = f"{prefix} " if prefix else ""
    badges = " ".join(f'<span class="sra-chip sra-chip-primary">{segment}</span>' for segment in segments)
    st.markdown(f"{label}{badges}", unsafe_allow_html=True)


def render_impact_badge(impact_score: float | None) -> None:
    if impact_score is None:
        st.caption("Impact score: —")
        return

    if impact_score >= 75:
        st.success(f"Impact score: **{impact_score:.0f}** / 100")
    elif impact_score >= 40:
        st.warning(f"Impact score: **{impact_score:.0f}** / 100")
    else:
        st.info(f"Impact score: **{impact_score:.0f}** / 100")
