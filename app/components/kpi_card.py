"""Reusable KPI metric card for Streamlit dashboards."""

from __future__ import annotations

import html

import streamlit as st


def render_kpi_card(
    label: str,
    value: str | int | float,
    *,
    help_text: str | None = None,
    delta: str | None = None,
) -> None:
    safe_label = html.escape(str(label))
    safe_value = html.escape(str(value))
    delta_html = (
        f'<div class="sra-kpi-delta">{html.escape(delta)}</div>' if delta else ""
    )
    title_attr = f' title="{html.escape(help_text)}"' if help_text else ""

    st.markdown(
        f"""
        <div class="sra-kpi-card"{title_attr}>
          <div class="sra-kpi-label">{safe_label}</div>
          <div class="sra-kpi-value">{safe_value}</div>
          {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
