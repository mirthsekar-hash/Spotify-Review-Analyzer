"""Trust score gauge for recommendation confidence."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from app.components.chart_theme import apply_dark_theme

_GAUGE_KEY_COUNTER = "_sra_trust_gauge_key_seq"


def _next_gauge_key(prefix: str = "trust_score_gauge") -> str:
    """Return a unique Streamlit key for each gauge instance on the page."""
    counter = int(st.session_state.get(_GAUGE_KEY_COUNTER, 0))
    st.session_state[_GAUGE_KEY_COUNTER] = counter + 1
    return f"{prefix}_{counter}"


def render_trust_score_gauge(score: float | None, *, key: str | None = None) -> None:
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
    st.plotly_chart(fig, use_container_width=True, key=key or _next_gauge_key())
