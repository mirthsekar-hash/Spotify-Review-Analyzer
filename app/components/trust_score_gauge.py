"""Trust score gauge for recommendation confidence."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from app.components.chart_theme import apply_dark_theme


def render_trust_score_gauge(score: float | None) -> None:
    if score is None:
        st.info("Trust score requires analyzed negative reviews.")
        return

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "/100"},
            title={"text": "Recommendation Trust Score"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#1DB954"},
                "steps": [
                    {"range": [0, 40], "color": "#3d2020"},
                    {"range": [40, 70], "color": "#3d3520"},
                    {"range": [70, 100], "color": "#1a3d28"},
                ],
            },
        )
    )
    fig.update_layout(margin=dict(t=40, b=20, l=30, r=30), height=320)
    apply_dark_theme(fig, height=320, margin=dict(t=40, b=20, l=30, r=30))
    st.plotly_chart(fig, use_container_width=True)
