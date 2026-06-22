"""Discovery Journey dashboard — Phase 3.8."""

from __future__ import annotations

import streamlit as st

from app.components.branding import render_page_header, render_section_title
from app.components.journey_flow_chart import render_journey_flow_table, render_journey_paths_chart
from app.components.journey_sankey import render_journey_steps
from src.services.journey_service import JourneyService, JourneyExplorerData


@st.cache_data(ttl=30, show_spinner="Loading discovery journeys...")
def load_journey_data(refresh_key: int) -> JourneyExplorerData:
  return JourneyService().get_journey_paths(limit=5)


def render_empty_state() -> None:
  st.info(
    "No journey paths available yet. Ingest reviews, run **Run Analysis**, and ensure "
    "reviews have `user_goal`, `listening_behavior`, `discovery_challenge`, and "
    "`primary_problem` populated."
  )


def render_paths_table(data: JourneyExplorerData) -> None:
  render_journey_flow_table(data.paths)


def render_path_detail(data: JourneyExplorerData) -> None:
  options = {path.summary: path for path in data.paths}
  selected_summary = st.selectbox(
    "Path detail",
    options=list(options.keys()),
    help="Select a journey path to inspect its steps and supporting review count",
  )
  selected = options[selected_summary]

  st.markdown(f"### Selected path")
  metric_cols = st.columns(3)
  metric_cols[0].metric("Supporting reviews", selected.frequency)
  metric_cols[1].metric("Negative sentiment", f"{selected.negative_pct:.1f}%")
  metric_cols[2].metric("Evidence IDs", len(selected.review_ids))

  render_journey_steps(selected)
  st.caption(
    "Chain format: user goal → listening behavior → discovery challenge → "
    "workaround (primary problem) → inferred desired outcome."
  )


def main() -> None:
  render_page_header(
    "Discovery Journey",
    "Top listener paths from goal to workaround and desired outcome",
  )

  refresh_key = st.session_state.get("data_version", 0)
  data = load_journey_data(refresh_key)

  if not data.db_connected:
    st.error("Cannot load journey data. Check Supabase connection.")
    return

  if len(data.paths) < 1:
    render_empty_state()
    return

  if len(data.paths) < 3:
    st.warning(
      f"Only {len(data.paths)} distinct journey path(s) found. "
      "Analyze more reviews to reach the target of 3+ paths."
    )

  overview_cols = st.columns(3)
  overview_cols[0].metric("Analyzed reviews", data.total_analyzed)
  overview_cols[1].metric("Top paths shown", len(data.paths))
  overview_cols[2].metric("Reviews in top paths", data.chain_count)

  render_section_title("Journey Flow")
  render_journey_paths_chart(data.paths, key="discovery_journey_paths_bar")

  render_section_title("Top Journey Paths")
  render_paths_table(data)

  render_section_title("Path Detail")
  render_path_detail(data)


main()
