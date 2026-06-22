"""Expandable review evidence list for explorer dashboards."""

from __future__ import annotations

import streamlit as st

from src.services.dashboard_service import SOURCE_LABELS


def render_evidence_list(
    reviews: list[dict],
    *,
    empty_message: str = "No supporting reviews available.",
    max_items: int | None = None,
) -> None:
    if not reviews:
        st.info(empty_message)
        return

    visible = reviews[:max_items] if max_items else reviews
    for index, review in enumerate(visible, start=1):
        source = review.get("source", "unknown")
        source_label = SOURCE_LABELS.get(source, str(source))
        rating = review.get("rating")
        rating_text = str(rating) if rating is not None else "n/a"
        preview = str(review.get("text", "")).strip()
        preview_short = preview[:80] + ("…" if len(preview) > 80 else "")

        with st.expander(f"Review {index} — {source_label} · ★ {rating_text} · {preview_short}"):
            st.write(preview or "No review text.")

    if max_items and len(reviews) > max_items:
        st.caption(f"Showing {max_items} of {len(reviews)} reviews.")
