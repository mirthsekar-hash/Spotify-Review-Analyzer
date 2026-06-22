"""Database and pipeline health indicator."""

from __future__ import annotations

import html
from datetime import datetime
from typing import Any

import streamlit as st

from src.services.dashboard_service import ExecutiveSummaryData


def _format_timestamp(value: datetime | str | None) -> str:
    if value is None:
        return "—"
    if isinstance(value, str):
        return value[:19].replace("T", " ")
    return value.strftime("%Y-%m-%d %H:%M UTC")


def _status_card(title: str, body: str, *, border_class: str) -> None:
    st.markdown(
        f"""
        <div class="sra-status-item {border_class}">
          <div class="sra-status-title">{html.escape(title)}</div>
          <div class="sra-status-body">{html.escape(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_health_indicator(
    summary: ExecutiveSummaryData,
    *,
    last_ingestion: dict[str, Any] | None = None,
    last_analysis: dict[str, Any] | None = None,
) -> None:
    if summary.db_connected:
        db_title = "Database connected"
        db_body = "Supabase is reachable"
        if summary.last_pipeline_run:
            run = summary.last_pipeline_run
            db_body = f"Last pipeline: {_format_timestamp(run.started_at)} ({run.status})"
        db_class = "sra-status-ok"
    else:
        db_title = "Database disconnected"
        db_body = "Check Supabase credentials"
        db_class = "sra-status-warn"

    if last_ingestion:
        ingest_title = "Last ingestion"
        ingest_body = (
            f"{last_ingestion.get('stored', 0)} stored from "
            f"{last_ingestion.get('source', 'unknown')}"
        )
        ingest_class = "sra-status-info"
    else:
        ingest_title = "Ingestion"
        ingest_body = "No ingestion run in this session"
        ingest_class = ""

    if last_analysis:
        analysis_title = "Last analysis"
        analysis_body = (
            f"{last_analysis.get('analyzed', 0)} analyzed, "
            f"{last_analysis.get('embedded', 0)} embedded"
        )
        analysis_class = "sra-status-ok"
    elif summary.pending_analysis > 0:
        analysis_title = "Analysis pending"
        analysis_body = f"{summary.pending_analysis} reviews awaiting analysis"
        analysis_class = "sra-status-warn"
    elif summary.total_analyzed > 0:
        analysis_title = "Analysis complete"
        analysis_body = f"{summary.total_analyzed} reviews fully analyzed"
        analysis_class = "sra-status-ok"
    else:
        analysis_title = "Analysis"
        analysis_body = "No analysis run in this session"
        analysis_class = ""

    col1, col2, col3 = st.columns(3)
    with col1:
        _status_card(db_title, db_body, border_class=db_class)
    with col2:
        _status_card(ingest_title, ingest_body, border_class=ingest_class)
    with col3:
        _status_card(analysis_title, analysis_body, border_class=analysis_class)
