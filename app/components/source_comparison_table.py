"""Source comparison table component."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.services.dashboard_service import SOURCE_LABELS, SourceAnalysisData


def _format_pct(value: float | None) -> str:
    return f"{value:.1f}%" if value is not None else "—"


def _format_rating(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "—"


def _format_sentiment_score(value: float | None) -> str:
    if value is None:
        return "—"
    if value >= 0.5:
        label = "Positive"
    elif value <= -0.5:
        label = "Negative"
    elif value >= 0:
        label = "Neutral / Mixed"
    else:
        label = "Mixed / Negative"
    return f"{value:+.2f} ({label})"


def render_source_comparison_table(data: SourceAnalysisData) -> None:
    rows = []
    for source, metrics in data.sources.items():
        rows.append(
            {
                "Source": SOURCE_LABELS.get(source, source),
                "Total reviews": metrics.review_count,
                "Analyzed": metrics.analyzed_count,
                "Avg rating": _format_rating(metrics.avg_rating),
                "Rec. complaint %": _format_pct(metrics.rec_complaint_pct),
                "Avg sentiment": _format_sentiment_score(metrics.avg_sentiment_score),
            }
        )

    if not rows or all(row["Total reviews"] == 0 for row in rows):
        st.info("No source data available yet.")
        return

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
