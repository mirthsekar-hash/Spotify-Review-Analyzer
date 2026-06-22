"""Sidebar pipeline orchestrator handlers."""

from __future__ import annotations

import streamlit as st

from src.db.client import check_connection
from src.db.repositories.pipeline_runs_repo import PipelineRunsRepository
from src.pipeline.orchestrator import CollectiveAnalysisResult, PipelineOrchestrator, PipelineResult


def handle_fetch_latest_reviews() -> None:
    if not check_connection():
        st.sidebar.error("Supabase not connected. Run the migration first.")
        return

    try:
        with st.sidebar.status("Running full pipeline…", expanded=True) as status:
            progress_lines: list[str] = []

            def on_progress(message: str) -> None:
                progress_lines.append(message)
                status.write(message)

            result = PipelineOrchestrator().run_full_pipeline_sync(
                progress_callback=on_progress,
            )
            status.update(
                label=f"Pipeline {result.status}",
                state="complete" if result.status != "failed" else "error",
            )

        _show_pipeline_result(result)
        st.session_state["last_pipeline"] = _pipeline_to_session(result)
        if result.collective and not result.collective.skipped:
            st.session_state["last_collective"] = _collective_to_session(result.collective)
        st.session_state["data_version"] = st.session_state.get("data_version", 0) + 1
    except Exception as exc:
        st.sidebar.error(f"Pipeline failed: {exc}")


def handle_rerun_collective_analysis() -> None:
    if not check_connection():
        st.sidebar.error("Supabase not connected. Run the migration first.")
        return

    try:
        with st.sidebar.status("Running collective analysis…", expanded=True) as status:
            progress_lines: list[str] = []

            def on_progress(message: str) -> None:
                progress_lines.append(message)
                status.write(message)

            result = PipelineOrchestrator().run_collective_analysis_sync(
                force=True,
                progress_callback=on_progress,
            )
            status.update(
                label=f"Collective analysis {result.status}",
                state="complete" if result.status != "failed" else "error",
            )

        _show_collective_result(result)
        st.session_state["last_collective"] = _collective_to_session(result)
        st.session_state["data_version"] = st.session_state.get("data_version", 0) + 1
    except Exception as exc:
        st.sidebar.error(f"Collective analysis failed: {exc}")


def render_pipeline_status_panel() -> None:
    """Show last pipeline run from DB or current session."""
    last_pipeline = st.session_state.get("last_pipeline")
    latest_run = None

    if check_connection():
        try:
            latest_run = PipelineRunsRepository().get_latest()
        except Exception:
            latest_run = None

    if latest_run:
        started = latest_run.get("started_at", "unknown")
        finished = latest_run.get("finished_at")
        status = latest_run.get("status", "unknown")
        stats = latest_run.get("stats") or {}
        st.sidebar.markdown(f"**Last pipeline:** `{status}`")
        st.sidebar.caption(f"Started: {started}")
        if finished:
            st.sidebar.caption(f"Finished: {finished}")
        _render_source_stats(stats.get("sources") or {})
        if stats.get("analyzed_count") is not None:
            st.sidebar.markdown(
                f"**Analyzed:** {stats.get('analyzed_count', 0)} | "
                f"**Embedded:** {stats.get('embedded_count', 0)}"
            )
        duration = stats.get("duration_seconds")
        if duration is not None:
            st.sidebar.caption(f"Duration: {duration}s")
        collective = stats.get("collective_analysis")
        if collective:
            st.sidebar.markdown(
                "**Collective:** "
                f"{collective.get('themes_written', 0)} themes, "
                f"{collective.get('segments_written', 0)} segments, "
                f"{collective.get('root_causes_written', 0)} root causes, "
                f"{collective.get('unmet_needs_written', 0)} unmet needs"
            )
    elif last_pipeline:
        st.sidebar.markdown(f"**Last pipeline:** `{last_pipeline.get('status', 'unknown')}`")
        _render_source_stats(last_pipeline.get("sources") or {})
        st.sidebar.markdown(
            f"**Analyzed:** {last_pipeline.get('analyzed', 0)} | "
            f"**Embedded:** {last_pipeline.get('embedded', 0)}"
        )
    else:
        st.sidebar.markdown("**Last pipeline:** Not yet executed")

    _render_collective_status_panel()


def _render_collective_status_panel() -> None:
    last_collective = st.session_state.get("last_collective")
    latest_collective = None

    if check_connection():
        try:
            latest_collective = PipelineRunsRepository().get_latest_collective_run()
        except Exception:
            latest_collective = None

    if latest_collective:
        stats = latest_collective.get("stats") or {}
        finished = latest_collective.get("finished_at")
        status = latest_collective.get("status", "unknown")
        st.sidebar.markdown(f"**Last collective:** `{status}`")
        if finished:
            st.sidebar.caption(f"Finished: {finished}")
        st.sidebar.caption(
            f"Themes: {stats.get('themes_written', 0)} | "
            f"Segments: {stats.get('segments_written', 0)} | "
            f"Root causes: {stats.get('root_causes_written', 0)} | "
            f"Unmet needs: {stats.get('unmet_needs_written', 0)}"
        )
        analyzed_at_run = stats.get("analyzed_review_count")
        if analyzed_at_run is not None:
            st.sidebar.caption(f"Analyzed reviews at run: {analyzed_at_run}")
    elif last_collective:
        st.sidebar.markdown(f"**Last collective:** `{last_collective.get('status', 'unknown')}`")
        st.sidebar.caption(
            f"Themes: {last_collective.get('themes_written', 0)} | "
            f"Segments: {last_collective.get('segments_written', 0)} | "
            f"Root causes: {last_collective.get('root_causes_written', 0)} | "
            f"Unmet needs: {last_collective.get('unmet_needs_written', 0)}"
        )
    else:
        st.sidebar.markdown("**Last collective:** Not yet executed")


def _show_pipeline_result(result: PipelineResult) -> None:
    if result.status == "success":
        st.sidebar.success(_summary_message(result))
    elif result.status == "partial":
        st.sidebar.warning(_summary_message(result))
        for source, source_result in result.sources.items():
            if source_result.error:
                st.sidebar.caption(f"{source}: {source_result.error}")
    else:
        st.sidebar.error("All sources failed. Try CSV import as fallback.")
        for source, source_result in result.sources.items():
            if source_result.error:
                st.sidebar.caption(f"{source}: {source_result.error}")


def _summary_message(result: PipelineResult) -> str:
    total_new = len(result.new_review_ids)
    message = (
        f"Pipeline {result.status}: {total_new} new reviews, "
        f"{result.analyzed_count} analyzed, {result.embedded_count} embedded "
        f"({result.duration_seconds:.1f}s)"
    )
    if result.collective and not result.collective.skipped:
        message += (
            f" | Collective: {result.collective.engines.themes_written} themes, "
            f"{result.collective.engines.segments_written} segments"
        )
    return message


def _show_collective_result(result: CollectiveAnalysisResult) -> None:
    if result.skipped:
        st.sidebar.info(result.skip_reason or "Collective analysis skipped")
        return

    if result.status == "success":
        st.sidebar.success(_collective_summary_message(result))
    elif result.status == "partial":
        st.sidebar.warning(_collective_summary_message(result))
        for error in result.engines.errors:
            st.sidebar.caption(error)
    else:
        st.sidebar.error("Collective analysis failed")
        for error in result.engines.errors:
            st.sidebar.caption(error)


def _collective_summary_message(result: CollectiveAnalysisResult) -> str:
    return (
        f"Collective {result.status}: "
        f"{result.engines.themes_written} themes, "
        f"{result.engines.segments_written} segments, "
        f"{result.engines.root_causes_written} root causes, "
        f"{result.engines.unmet_needs_written} unmet needs "
        f"({result.duration_seconds:.1f}s)"
    )


def _collective_to_session(result: CollectiveAnalysisResult) -> dict:
    return {
        "status": result.status,
        "themes_written": result.engines.themes_written,
        "segments_written": result.engines.segments_written,
        "root_causes_written": result.engines.root_causes_written,
        "unmet_needs_written": result.engines.unmet_needs_written,
        "duration_seconds": result.duration_seconds,
        "skipped": result.skipped,
    }


def _pipeline_to_session(result: PipelineResult) -> dict:
    return {
        "status": result.status,
        "sources": {
            name: {
                "fetched": source.fetched,
                "stored": source.stored,
                "new": source.new,
                "error": source.error,
                "used_fallback": source.used_fallback,
            }
            for name, source in result.sources.items()
        },
        "analyzed": result.analyzed_count,
        "embedded": result.embedded_count,
        "duration_seconds": result.duration_seconds,
    }


def _render_source_stats(sources: dict) -> None:
    if not sources:
        return

    for source in ("playstore", "appstore", "reddit"):
        data = sources.get(source)
        if not data:
            continue
        if data.get("error"):
            st.sidebar.caption(f"{source}: failed — {data['error']}")
        else:
            fallback_note = " (CSV fallback)" if data.get("used_fallback") else ""
            st.sidebar.caption(
                f"{source}: {data.get('stored', 0)} stored, "
                f"{data.get('new', 0)} new{fallback_note}"
            )
