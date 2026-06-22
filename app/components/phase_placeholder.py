"""Render a placeholder dashboard page until the phase is implemented."""

from __future__ import annotations

import streamlit as st


def render_phase_placeholder(title: str, phase: str, description: str) -> None:
    st.title(title)
    st.info(f"**{phase}** — {description}")
    st.markdown(
        """
        Use the sidebar to:
        - **Fetch Latest Reviews** — automated ingestion (Phase 2)
        - **Import CSV (Fallback)** — manual data import (Phase 1.3)
        - **Pipeline Status** — last run and progress
        """
    )
