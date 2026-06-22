"""Readable journey path charts and tables (replaces cluttered Sankey)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.components.chart_theme import apply_dark_theme
from src.services.journey_service import JOURNEY_STAGES, STAGE_LABELS, JourneyPath


def _path_chart_label(path: JourneyPath, rank: int) -> str:
    challenge = path.steps[2]
    if len(challenge) > 48:
        challenge = challenge[:47].rstrip() + "…"
    return f"#{rank} · {challenge}"


def render_journey_paths_chart(
    paths: list[JourneyPath],
    *,
    key: str = "journey_paths_bar",
) -> None:
    if not paths:
        st.info("Not enough journey data to chart top paths.")
        return

    labels = [_path_chart_label(path, rank) for rank, path in enumerate(paths, start=1)]
    values = [path.frequency for path in paths]
    hover = [
        (
            f"<b>{label}</b><br>"
            f"Reviews: {path.frequency}<br>"
            f"Negative: {path.negative_pct:.1f}%<br>"
            f"Goal: {path.steps[0]}<br>"
            f"Behavior: {path.steps[1]}<br>"
            f"Workaround: {path.steps[3]}<br>"
            f"Outcome: {path.steps[4]}"
        )
        for label, path in zip(labels, paths, strict=True)
    ]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color="#1DB954",
            hovertemplate="%{customdata}<extra></extra>",
            customdata=hover,
        )
    )
    fig.update_layout(
        xaxis_title="Supporting reviews",
        yaxis=dict(autorange="reversed"),
        height=max(280, 72 * len(paths)),
    )
    apply_dark_theme(
        fig,
        title="Top journey paths by review count",
        height=max(280, 72 * len(paths)),
        margin=dict(t=50, b=40, l=20, r=20),
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


def render_journey_flow_table(paths: list[JourneyPath]) -> None:
    if not paths:
        return

    rows = []
    for rank, path in enumerate(paths, start=1):
        row = {
            "Rank": rank,
            "Reviews": path.frequency,
            "Negative %": f"{path.negative_pct:.1f}%",
        }
        for stage, label in zip(JOURNEY_STAGES, path.steps, strict=True):
            row[STAGE_LABELS[stage]] = label
        rows.append(row)

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
