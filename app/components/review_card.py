"""Review card for Review Discovery browse list."""

from __future__ import annotations

import html
from datetime import datetime

import streamlit as st

from src.db.models import Review
from src.services.dashboard_service import SOURCE_LABELS

RATING_STAR_COLORS = {
    5: "#1DB954",
    4: "#53E076",
    3: "#F5C518",
    2: "#FF8C42",
    1: "#E91429",
}


def _format_date(value: datetime | None) -> str:
    if value is None:
        return "—"
    return value.strftime("%Y-%m-%d")


def _metadata_value(review: Review, *keys: str) -> str | None:
    metadata = review.metadata or {}
    for key in keys:
        raw = metadata.get(key)
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    return None


def _render_stars(rating: int | None) -> str:
    if rating is None:
        return '<span class="sra-review-stars">No rating</span>'
    color = RATING_STAR_COLORS.get(rating, "#b3b3b3")
    filled = "★" * rating
    empty = "☆" * (5 - rating)
    return (
        f'<span class="sra-review-stars" style="color:{color};">'
        f"{filled}<span style=\"color:#555;\">{empty}</span></span>"
    )


def render_review_card(review: Review) -> None:
    source_label = SOURCE_LABELS.get(review.source, review.source)
    version = _metadata_value(review, "review_created_version", "app_version", "version")
    helpful = _metadata_value(review, "helpful_count", "thumbsUpCount", "upvotes")
    review_text = html.escape(review.text or "")
    review_id = html.escape(str(review.id))
    date_label = _format_date(review.review_date or review.created_at)
    version_html = f"v{html.escape(version)}" if version else ""
    helpful_html = f"👍 {html.escape(helpful)}" if helpful else ""

    meta_parts = [part for part in (date_label, version_html, helpful_html, review_id) if part]
    meta_line = " · ".join(meta_parts)

    st.markdown(
        f"""
        <div class="sra-review-card">
          <div class="sra-review-card-header">
            {_render_stars(review.rating)}
            <span class="sra-review-source">{html.escape(source_label)}</span>
          </div>
          <p class="sra-review-text">{review_text}</p>
          <div class="sra-review-meta">{meta_line}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
