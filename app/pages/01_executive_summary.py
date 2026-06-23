"""Executive Summary dashboard — Phase 1.5."""

from __future__ import annotations

import streamlit as st

from app.components.branding import render_page_header, render_section_title
from app.components.executive_ai_summary import render_executive_ai_summary_from_cache
from app.components.health_indicator import render_health_indicator
from app.components.kpi_card import render_kpi_card
from app.components.sentiment_chart import render_sentiment_chart
from app.components.trust_score_gauge import render_trust_score_gauge
from app.components.segment_priority_panel import render_segment_priority_panel
from src.llm.errors import LlmQuotaExceededError
from src.services.dashboard_service import DashboardService, ExecutiveSummaryData, SegmentPriorityData


@st.cache_data(ttl=3600, show_spinner="Generating AI executive summary...")
def load_ai_executive_summary(refresh_key: int) -> dict | None:
    """Cache busts when refresh_key (data_version) changes after collective analysis."""
    try:
        result = DashboardService().generate_executive_summary()
    except LlmQuotaExceededError as exc:
        return {"available": False, "reason": str(exc)}
    except Exception as exc:
        return {"available": False, "reason": f"Could not generate summary: {exc}"}

    if result is None:
        return None
    return {
        "available": result.available,
        "reason": result.reason,
        "output": result.output.model_dump() if result.output else None,
        "theme_count": result.theme_count,
        "segment_count": result.segment_count,
        "root_cause_count": result.root_cause_count,
        "unmet_need_count": result.unmet_need_count,
    }


@st.cache_data(ttl=30, show_spinner="Loading dashboard data...")
def load_executive_summary(refresh_key: int) -> ExecutiveSummaryData:
    return DashboardService().get_executive_summary()


@st.cache_data(ttl=30, show_spinner="Ranking user segments...")
def load_segment_priority(refresh_key: int) -> SegmentPriorityData:
    return DashboardService().get_segment_priority()


def render_empty_state() -> None:
    st.info(
        "No reviews in the database yet. Use the sidebar to **Import CSV** "
        "or **Fetch Play Store Reviews**, then click **Run Analysis**."
    )


def render_partial_analysis_banner(summary) -> None:
    if summary.total_reviews == 0:
        return
    if summary.pending_analysis > 0:
        st.warning(
            f"**{summary.total_analyzed} of {summary.total_reviews}** reviews analyzed. "
            f"Click **Run Analysis** in the sidebar to process the remaining "
            f"{summary.pending_analysis}."
        )


def main() -> None:
    render_page_header(
        "Executive Summary",
        "Product research intelligence across ingested Spotify feedback",
    )

    refresh_key = st.session_state.get("data_version", 0)
    summary = load_executive_summary(refresh_key)

    render_health_indicator(
        summary,
        last_ingestion=st.session_state.get("last_ingestion"),
        last_analysis=st.session_state.get("last_analysis"),
    )
    st.divider()

    if not summary.db_connected:
        st.error(
            "Cannot load dashboard data. Check Supabase credentials and run "
            "`supabase/migrations/001_initial_schema.sql`."
        )
        return

    if summary.total_reviews == 0:
        render_empty_state()
        return

    render_partial_analysis_banner(summary)

    render_section_title("Portfolio Overview")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        render_kpi_card(
            "Reviews Ingested",
            f"{summary.total_reviews:,}",
            help_text="Total reviews stored across all sources",
        )
    with kpi2:
        render_kpi_card(
            "Themes Discovered",
            summary.themes_discovered,
            help_text="Distinct themes from collective analysis",
        )
    with kpi3:
        rating_display = (
            f"{summary.avg_rating:.2f}★"
            if summary.avg_rating is not None
            else "—"
        )
        render_kpi_card(
            "Avg Rating",
            rating_display,
            help_text="Average star rating across ingested reviews with ratings",
        )
    with kpi4:
        render_kpi_card(
            "Analysis Sample",
            f"{summary.total_analyzed:,}",
            help_text="Reviews with completed analysis and embeddings",
            delta=f"{summary.pending_analysis:,} pending" if summary.pending_analysis else None,
        )

    render_section_title("AI Executive Summary")
    ai_summary = load_ai_executive_summary(refresh_key)
    render_executive_ai_summary_from_cache(ai_summary)
    st.divider()

    render_section_title("Research Highlights")
    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        render_kpi_card(
            "Top Discovery Challenge",
            summary.top_discovery_challenge or "—",
            help_text="Most frequently cited discovery challenge",
        )
    with kpi2:
        segment_label = summary.most_affected_segment or "—"
        if summary.segment_negative_rate is not None:
            segment_label = f"{segment_label} ({summary.segment_negative_rate}% neg)"
        render_kpi_card(
            "Most Affected Segment",
            segment_label,
            help_text="User segment with the highest share of negative sentiment",
        )
    with kpi3:
        trust_display = (
            f"{summary.recommendation_trust_score:.0f}"
            if summary.recommendation_trust_score is not None
            else "—"
        )
        render_kpi_card(
            "Recommendation Trust",
            trust_display,
            help_text="100 minus rec-complaint rate among negative reviews (0–100)",
        )

    render_section_title("Segment Priority")
    segment_priority = load_segment_priority(refresh_key)
    render_segment_priority_panel(segment_priority)
    st.divider()

    chart_col, gauge_col = st.columns([1.2, 1])
    with chart_col:
        render_section_title("Sentiment Breakdown")
        render_sentiment_chart(summary.sentiment)
        if summary.sentiment.total > 0:
            st.caption(
                f"Positive {summary.sentiment.positive_pct}% · "
                f"Negative {summary.sentiment.negative_pct}% · "
                f"Neutral {summary.sentiment.neutral_pct}% · "
                f"Mixed {summary.sentiment.mixed_pct}%"
            )
    with gauge_col:
        render_section_title("Trust Score")
        render_trust_score_gauge(summary.recommendation_trust_score)

    if summary.top_discovery_challenge:
        render_section_title("Top Challenge Detail")
        st.markdown(
            f"**{summary.top_discovery_challenge}** appears in "
            f"**{summary.top_discovery_challenge_count}** analyzed reviews."
        )


main()
