"""Horizontal rating distribution chart for Review Discovery."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from app.components.chart_theme import apply_dark_theme
from src.services.review_discovery_service import RatingDistribution

RATING_COLORS = {
    5: "#1DB954",
    4: "#53E076",
    3: "#F5C518",
    2: "#FF8C42",
    1: "#E91429",
}


def render_rating_distribution_chart(
    distribution: RatingDistribution,
    *,
    key: str = "review_discovery_rating_dist",
) -> None:
    labels = [f"{star}★" for star in range(5, 0, -1)]
    values = [distribution.counts.get(star, 0) for star in range(5, 0, -1)]
    colors = [RATING_COLORS[star] for star in range(5, 0, -1)]

    if distribution.total_with_rating == 0:
        st.info("No rated reviews match the current filters.")
        return

    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=colors,
            text=values,
            textposition="outside",
            hovertemplate="%{y}: %{x} reviews<extra></extra>",
        )
    )
    fig.update_layout(
        xaxis_title="Reviews",
        yaxis=dict(autorange="reversed"),
        height=260,
    )
    apply_dark_theme(
        fig,
        title="Rating distribution",
        height=260,
        margin=dict(t=50, b=40, l=20, r=40),
    )
    st.plotly_chart(fig, use_container_width=True, key=key)
