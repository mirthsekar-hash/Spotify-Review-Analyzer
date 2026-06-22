"""Plotly Sankey diagram for discovery journey paths."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from app.components.chart_theme import apply_dark_theme

from src.services.journey_service import (
    JOURNEY_STAGES,
    STAGE_LABELS,
    JourneyPath,
    SankeyDiagramData,
)


def render_journey_sankey(diagram: SankeyDiagramData) -> None:
    if not diagram.labels or not diagram.values:
        st.info("Not enough journey data to render a Sankey diagram.")
        return

    fig = go.Figure(
        data=[
            go.Sankey(
                arrangement="snap",
                node={
                    "label": diagram.labels,
                    "pad": 18,
                    "thickness": 18,
                    "color": "#1DB954",
                    "line": {"color": "#191414", "width": 0.4},
                },
                link={
                    "source": diagram.sources,
                    "target": diagram.targets,
                    "value": diagram.values,
                    "hovertemplate": "%{customdata}<br>Reviews: %{value}<extra></extra>",
                    "customdata": diagram.link_labels,
                    "color": "rgba(29, 185, 84, 0.35)",
                },
            )
        ]
    )
    fig.update_layout(
        title="Discovery Journey Flow",
        margin=dict(t=50, b=20, l=20, r=20),
        height=520,
        font=dict(size=11),
    )
    apply_dark_theme(
        fig,
        title="Discovery Journey Flow",
        height=520,
        margin=dict(t=50, b=20, l=20, r=20),
        font=dict(size=11),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_journey_steps(path: JourneyPath) -> None:
    columns = st.columns(len(JOURNEY_STAGES))
    for column, stage, label in zip(columns, JOURNEY_STAGES, path.steps, strict=True):
        with column:
            st.markdown(f"**{STAGE_LABELS[stage]}**")
            st.markdown(label)
