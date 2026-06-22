"""Unmet Needs & Opportunities dashboard — Phase 3.7."""

from __future__ import annotations

from uuid import UUID

import plotly.graph_objects as go
import streamlit as st

from app.components.branding import render_page_header, render_section_title
from app.components.chart_theme import apply_dark_theme

from app.components.evidence_list import render_evidence_list
from src.db.repositories.reviews_repo import ReviewsRepository
from src.services.explorer_service import ExplorerService, UnmetNeedsExplorerData


@st.cache_data(ttl=30, show_spinner="Loading unmet needs...")
def load_unmet_needs(refresh_key: int) -> UnmetNeedsExplorerData:
    return ExplorerService().get_unmet_needs()


@st.cache_data(ttl=30, show_spinner="Loading supporting reviews...")
def load_reviews_for_need(review_ids: tuple[str, ...], refresh_key: int) -> list[dict]:
    if not review_ids:
        return []
    repo = ReviewsRepository()
    reviews = repo.get_by_ids([UUID(review_id) for review_id in review_ids])
    return [
        {
            "id": str(review.id),
            "source": review.source,
            "text": review.text,
            "rating": review.rating,
        }
        for review in reviews
    ]


def render_empty_state() -> None:
    st.info(
        "No unmet needs detected yet. Re-run collective analysis after more reviews "
        "are analyzed, or check that the unmet needs engine completed successfully."
    )


def render_opportunity_matrix(data: UnmetNeedsExplorerData) -> None:
    labeled_needs = [item for item in data.needs if item.opportunity_score is not None]
    if not labeled_needs:
        st.info("No opportunity scores available to plot.")
        return

    fig = go.Figure(
        data=[
            go.Scatter(
                x=[item.frequency for item in labeled_needs],
                y=[item.opportunity_score for item in labeled_needs],
                mode="markers+text",
                text=[item.need[:40] + ("…" if len(item.need) > 40 else "") for item in labeled_needs],
                textposition="top center",
                marker={
                    "size": 12,
                    "color": [item.opportunity_score for item in labeled_needs],
                    "colorscale": "Viridis",
                    "showscale": True,
                    "colorbar": {"title": "Opportunity"},
                },
                hovertemplate=(
                    "%{text}<br>Frequency: %{x}<br>Opportunity: %{y}<extra></extra>"
                ),
            )
        ]
    )
    fig.update_layout(
        title="Opportunity Matrix",
        xaxis_title="Frequency",
        yaxis_title="Opportunity score",
        margin=dict(t=50, b=40, l=40, r=20),
        height=460,
    )
    apply_dark_theme(
        fig,
        title="Opportunity Matrix",
        xaxis_title="Frequency",
        yaxis_title="Opportunity score",
        height=460,
        margin=dict(t=50, b=40, l=40, r=20),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_solution_cards(data: UnmetNeedsExplorerData) -> None:
    render_section_title("AI Solution Ideas")
    for item in data.needs:
        with st.container(border=True):
            score = f"{item.opportunity_score:.0f}" if item.opportunity_score is not None else "—"
            st.markdown(f"**{item.need}**")
            st.caption(f"Frequency: {item.frequency} · Opportunity: {score}")
            if item.suggested_ai_solutions:
                for solution in item.suggested_ai_solutions:
                    st.markdown(f"- {solution}")
            else:
                st.caption("No AI solutions suggested.")

            if item.supporting_review_ids:
                review_key = tuple(str(rid) for rid in item.supporting_review_ids)
                refresh_key = st.session_state.get("data_version", 0)
                reviews = load_reviews_for_need(review_key, refresh_key)
                with st.expander("Supporting reviews"):
                    render_evidence_list(reviews, empty_message="Supporting reviews not found.")


def main() -> None:
    render_page_header(
        "Unmet Needs & Opportunities",
        "Product gaps, opportunity scores, and suggested AI solutions",
    )

    refresh_key = st.session_state.get("data_version", 0)
    data = load_unmet_needs(refresh_key)

    if not data.db_connected:
        st.error("Cannot load unmet needs. Check Supabase connection.")
        return

    if not data.needs:
        render_empty_state()
        return

    render_opportunity_matrix(data)
    render_solution_cards(data)


main()
