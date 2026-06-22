"""Sentiment breakdown chart components."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from app.components.chart_theme import apply_dark_theme
from src.services.dashboard_service import SOURCE_LABELS, SentimentBreakdown, SourceMetrics

SENTIMENT_COLORS = {
    "positive": "#1DB954",
    "negative": "#E91429",
    "neutral": "#B3B3B3",
    "mixed": "#FFA500",
}

SENTIMENT_LABELS = {
    "positive": "Positive",
    "negative": "Negative",
    "neutral": "Neutral",
    "mixed": "Mixed",
}


def render_sentiment_chart(breakdown: SentimentBreakdown) -> None:
    if breakdown.total == 0:
        st.info("No sentiment data yet. Run analysis on ingested reviews.")
        return

    labels: list[str] = []
    values: list[int] = []
    colors: list[str] = []
    for sentiment in ("positive", "negative", "neutral", "mixed"):
        count = breakdown.counts[sentiment]
        if count > 0:
            labels.append(SENTIMENT_LABELS[sentiment])
            values.append(count)
            colors.append(SENTIMENT_COLORS[sentiment])

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.45,
                marker={"colors": colors},
                textinfo="label+percent",
                hovertemplate="%{label}: %{value} reviews (%{percent})<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        margin=dict(t=20, b=20, l=20, r=20),
        height=360,
        showlegend=False,
    )
    apply_dark_theme(fig, height=360, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


def render_review_count_by_source(sources: dict[str, SourceMetrics]) -> None:
    labels = [SOURCE_LABELS.get(source, source) for source in sources]
    values = [metrics.review_count for metrics in sources.values()]

    if sum(values) == 0:
        st.info("No reviews ingested yet.")
        return

    fig = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=values,
                marker_color=["#1DB954", "#007AFF", "#FF4500"],
                hovertemplate="%{x}: %{y} reviews<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        margin=dict(t=20, b=40, l=20, r=20),
        height=360,
        yaxis_title="Reviews",
        xaxis_title="Source",
    )
    apply_dark_theme(fig, height=360, yaxis_title="Reviews", xaxis_title="Source")
    st.plotly_chart(fig, use_container_width=True)


def render_sentiment_by_source_chart(sources: dict[str, SourceMetrics]) -> None:
    analyzed_total = sum(metrics.analyzed_count for metrics in sources.values())
    if analyzed_total == 0:
        st.info("No analyzed reviews yet. Run analysis from the sidebar.")
        return

    source_keys = list(sources.keys())
    labels = [SOURCE_LABELS.get(source, source) for source in source_keys]
    fig = go.Figure()

    for sentiment in ("positive", "negative", "neutral", "mixed"):
        values = [sources[source].sentiment.counts[sentiment] for source in source_keys]
        if sum(values) == 0:
            continue
        fig.add_trace(
            go.Bar(
                name=SENTIMENT_LABELS[sentiment],
                x=labels,
                y=values,
                marker_color=SENTIMENT_COLORS[sentiment],
                hovertemplate="%{x}<br>%{fullData.name}: %{y}<extra></extra>",
            )
        )

    fig.update_layout(
        barmode="stack",
        margin=dict(t=20, b=40, l=20, r=20),
        height=400,
        yaxis_title="Analyzed reviews",
        xaxis_title="Source",
        legend_title="Sentiment",
    )
    apply_dark_theme(
        fig,
        barmode="stack",
        height=400,
        yaxis_title="Analyzed reviews",
        xaxis_title="Source",
        legend_title="Sentiment",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_segment_distribution_chart(segment_counts: dict[str, int]) -> None:
    if not segment_counts:
        st.info("No segment distribution available for this selection.")
        return

    labels = list(segment_counts.keys())
    values = list(segment_counts.values())
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.4,
                textinfo="label+percent",
                hovertemplate="%{label}: %{value} reviews (%{percent})<extra></extra>",
            )
        ]
    )
    fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=360, showlegend=False)
    apply_dark_theme(fig, height=360, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
