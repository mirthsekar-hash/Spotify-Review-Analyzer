"""Readable unmet needs charts and tables (replaces cluttered scatter matrix)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.components.chart_theme import apply_dark_theme
from src.db.models import UnmetNeed


def _priority_label(score: float | None) -> str:
    if score is None:
        return "—"
    if score >= 70:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


def _sort_needs(needs: list[UnmetNeed]) -> list[UnmetNeed]:
    return sorted(
        needs,
        key=lambda item: (
            -(item.opportunity_score or 0),
            -item.frequency,
            item.need,
        ),
    )


def _chart_label(need: str, rank: int, *, max_length: int = 52) -> str:
    text = need.strip()
    if len(text) > max_length:
        text = text[: max_length - 1].rstrip() + "…"
    return f"#{rank} · {text}"


def render_unmet_needs_ranking_chart(
    needs: list[UnmetNeed],
    *,
    key: str = "unmet_needs_ranking_bar",
) -> None:
    scored = [item for item in needs if item.opportunity_score is not None]
    if not scored:
        st.info("No opportunity scores available to chart.")
        return

    ranked = _sort_needs(scored)
    labels = [_chart_label(item.need, rank) for rank, item in enumerate(ranked, start=1)]
    values = [item.opportunity_score or 0 for item in ranked]
    colors = values
    hover = [
        (
            f"<b>{item.need}</b><br>"
            f"Opportunity: {item.opportunity_score:.0f}<br>"
            f"Frequency: {item.frequency}<br>"
            f"Priority: {_priority_label(item.opportunity_score)}"
        )
        for item in ranked
    ]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker={
                "color": colors,
                "colorscale": [[0, "#509BF5"], [0.5, "#1DB954"], [1, "#F5C518"]],
                "showscale": True,
                "colorbar": {"title": "Score"},
            },
            hovertemplate="%{customdata}<extra></extra>",
            customdata=hover,
        )
    )
    fig.update_layout(
        xaxis_title="Opportunity score",
        yaxis=dict(autorange="reversed"),
        height=max(320, 56 * len(ranked)),
    )
    apply_dark_theme(
        fig,
        title="Top unmet needs by opportunity score",
        height=max(320, 56 * len(ranked)),
        margin=dict(t=50, b=40, l=20, r=40),
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


def render_unmet_needs_summary_table(needs: list[UnmetNeed]) -> None:
    if not needs:
        return

    ranked = _sort_needs(needs)
    rows = [
        {
            "Rank": rank,
            "Unmet need": item.need,
            "Frequency": item.frequency,
            "Opportunity": (
                f"{item.opportunity_score:.0f}"
                if item.opportunity_score is not None
                else "—"
            ),
            "Priority": _priority_label(item.opportunity_score),
        }
        for rank, item in enumerate(ranked, start=1)
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
