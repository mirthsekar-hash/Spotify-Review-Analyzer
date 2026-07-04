"""Unmet Needs & Opportunities dashboard — Phase 3.7."""

from __future__ import annotations

from uuid import UUID

import streamlit as st

from app.components.branding import render_page_header, render_section_title
from app.components.evidence_list import render_evidence_list
from app.components.unmet_needs_chart import (
    render_unmet_needs_ranking_chart,
    render_unmet_needs_summary_table,
)
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


def render_solution_cards(data: UnmetNeedsExplorerData) -> None:
    render_section_title("AI Solution Ideas")
    sorted_needs = sorted(
        data.needs,
        key=lambda item: (-(item.opportunity_score or 0), -item.frequency, item.need),
    )
    for item in sorted_needs:
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

    render_section_title("Opportunity Ranking")
    render_unmet_needs_ranking_chart(data.needs, key="unmet_needs_opportunity_bar")

    render_section_title("Unmet Needs Summary")
    render_unmet_needs_summary_table(data.needs)
    st.caption(
        "Priority bands: High (70+), Medium (40–69), Low (&lt;40). "
        "Sorted by opportunity score, then frequency."
    )

    render_solution_cards(data)


main()
