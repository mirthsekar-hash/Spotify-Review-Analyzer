"""Review Discovery page — Phase 2.6."""

from __future__ import annotations

import streamlit as st

from app.components.branding import render_page_header, render_section_title
from app.components.kpi_card import render_kpi_card
from app.components.rating_distribution_chart import render_rating_distribution_chart
from app.components.review_card import render_review_card
from src.db.models import ReviewSource
from src.db.repositories.reviews_repo import ReviewSearchParams, ReviewSortOrder
from src.services.review_discovery_service import ReviewDiscoveryData, ReviewDiscoveryService

PAGE_SIZE = 40
SORT_OPTIONS: dict[str, ReviewSortOrder] = {
    "Oldest first": "oldest",
    "Newest first": "newest",
    "Highest rating": "rating_high",
    "Lowest rating": "rating_low",
}
RATING_OPTIONS = {
    "All": None,
    "5★": 5,
    "4★": 4,
    "3★": 3,
    "2★": 2,
    "1★": 1,
}
SOURCE_OPTIONS: dict[str, ReviewSource | None] = {
    "All sources": None,
    "Play Store": "playstore",
    "App Store": "appstore",
    "Reddit": "reddit",
}


def _filter_signature(
    query: str,
    rating_label: str,
    source_label: str,
    sort_label: str,
) -> tuple[str, str, str, str]:
    return (query.strip(), rating_label, source_label, sort_label)


def _build_params(
    query: str,
    rating_label: str,
    source_label: str,
    sort_label: str,
) -> ReviewSearchParams:
    return ReviewSearchParams(
        query=query.strip() or None,
        rating=RATING_OPTIONS[rating_label],
        source=SOURCE_OPTIONS[source_label],
        sort_by=SORT_OPTIONS[sort_label],
    )


@st.cache_data(ttl=30, show_spinner="Searching reviews...")
def load_review_discovery(
    query: str,
    rating_label: str,
    source_label: str,
    sort_label: str,
    page: int,
    refresh_key: int,
) -> ReviewDiscoveryData:
    params = _build_params(query, rating_label, source_label, sort_label)
    return ReviewDiscoveryService().search(params, page=page, page_size=PAGE_SIZE)


def render_empty_state() -> None:
    st.info(
        "No reviews in the database yet. Use the sidebar to **Fetch Latest Reviews** "
        "or **Import CSV**, then return here to browse the corpus."
    )


def render_filters(
    query: str,
    rating_label: str,
    source_label: str,
    sort_label: str,
) -> tuple[str, str, str, str, bool]:
    st.markdown("**Filters**")
    query = st.text_input(
        "Search reviews",
        value=query,
        placeholder='Try "shuffle", "Discover Weekly", "ads"…',
        help="Keyword search across review text",
    )
    rating_label = st.radio(
        "Rating",
        options=list(RATING_OPTIONS.keys()),
        index=list(RATING_OPTIONS.keys()).index(rating_label),
        horizontal=False,
    )
    sort_label = st.selectbox(
        "Sort by",
        options=list(SORT_OPTIONS.keys()),
        index=list(SORT_OPTIONS.keys()).index(sort_label),
    )
    source_label = st.selectbox(
        "Source",
        options=list(SOURCE_OPTIONS.keys()),
        index=list(SOURCE_OPTIONS.keys()).index(source_label),
    )
    reset_clicked = st.button("Reset filters", use_container_width=True, type="primary")
    return query, rating_label, source_label, sort_label, reset_clicked


def render_pagination(data: ReviewDiscoveryData) -> None:
    if data.matching_count <= data.page_size:
        return

    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("← Previous", disabled=data.page <= 1, use_container_width=True):
            st.session_state.review_discovery_page = max(data.page - 1, 1)
            st.rerun()
    with col_info:
        start = (data.page - 1) * data.page_size + 1 if data.matching_count else 0
        end = min(data.page * data.page_size, data.matching_count)
        st.markdown(
            f"<p style='text-align:center;color:#b3b3b3;margin:0.5rem 0;'>"
            f"Page {data.page} of {data.total_pages} · showing {start}–{end}</p>",
            unsafe_allow_html=True,
        )
    with col_next:
        if st.button("Next →", disabled=data.page >= data.total_pages, use_container_width=True):
            st.session_state.review_discovery_page = min(data.page + 1, data.total_pages)
            st.rerun()


def render_results(data: ReviewDiscoveryData) -> None:
    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        rating_display = f"{data.avg_rating:.2f}★" if data.avg_rating is not None else "—"
        render_kpi_card(
            "Avg Rating",
            rating_display,
            help_text="Average star rating for reviews matching search and source filters",
        )
    with kpi2:
        render_kpi_card(
            "Matching Reviews",
            f"{data.matching_count:,}",
            help_text="Reviews matching all active filters",
        )
    with kpi3:
        render_kpi_card(
            "Corpus Total",
            f"{data.corpus_total:,}",
            help_text="Total reviews stored across all sources",
        )

    render_section_title("Rating Distribution")
    render_rating_distribution_chart(
        data.rating_distribution,
        key="review_discovery_rating_distribution",
    )

    render_section_title("Discovered Reviews")
    if data.matching_count == 0:
        st.warning("No reviews match the current filters. Try broadening your search or resetting filters.")
        return

    visible_start = (data.page - 1) * data.page_size + 1
    visible_end = min(data.page * data.page_size, data.matching_count)
    st.caption(f"{visible_end - visible_start + 1} of {data.matching_count:,} matching reviews on this page")

    for review in data.reviews:
        render_review_card(review)

    render_pagination(data)


def main() -> None:
    render_page_header(
        "Review Discovery",
        "Search, filter, and browse the raw review corpus",
    )

    if "review_discovery_query" not in st.session_state:
        st.session_state.review_discovery_query = ""
    if "review_discovery_rating" not in st.session_state:
        st.session_state.review_discovery_rating = "All"
    if "review_discovery_source" not in st.session_state:
        st.session_state.review_discovery_source = "All sources"
    if "review_discovery_sort" not in st.session_state:
        st.session_state.review_discovery_sort = "Oldest first"
    if "review_discovery_page" not in st.session_state:
        st.session_state.review_discovery_page = 1
    if "review_discovery_filter_sig" not in st.session_state:
        st.session_state.review_discovery_filter_sig = _filter_signature("", "All", "All sources", "Oldest first")

    filter_col, results_col = st.columns([1, 3.2], gap="large")

    with filter_col:
        query, rating_label, source_label, sort_label, reset_clicked = render_filters(
            st.session_state.review_discovery_query,
            st.session_state.review_discovery_rating,
            st.session_state.review_discovery_source,
            st.session_state.review_discovery_sort,
        )

    if reset_clicked:
        st.session_state.review_discovery_query = ""
        st.session_state.review_discovery_rating = "All"
        st.session_state.review_discovery_source = "All sources"
        st.session_state.review_discovery_sort = "Oldest first"
        st.session_state.review_discovery_page = 1
        st.session_state.review_discovery_filter_sig = _filter_signature("", "All", "All sources", "Oldest first")
        st.rerun()

    st.session_state.review_discovery_query = query
    st.session_state.review_discovery_rating = rating_label
    st.session_state.review_discovery_source = source_label
    st.session_state.review_discovery_sort = sort_label

    current_sig = _filter_signature(query, rating_label, source_label, sort_label)
    if current_sig != st.session_state.review_discovery_filter_sig:
        st.session_state.review_discovery_filter_sig = current_sig
        st.session_state.review_discovery_page = 1

    refresh_key = st.session_state.get("data_version", 0)
    data = load_review_discovery(
        query,
        rating_label,
        source_label,
        sort_label,
        st.session_state.review_discovery_page,
        refresh_key,
    )

    with results_col:
        if not data.db_connected:
            st.error("Cannot load reviews. Check Supabase connection and migration.")
            return

        if data.corpus_total == 0:
            render_empty_state()
            return

        render_results(data)


main()
