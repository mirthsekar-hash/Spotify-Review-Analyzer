"""Sidebar ingestion handlers."""

from __future__ import annotations

import streamlit as st

from src.db.client import SupabaseConfigurationError, check_connection
from src.ingestion.csv_importer import CSVImportError
from src.ingestion.exceptions import RedditFetchError, ScrapeError
from src.ingestion.service import IngestionService
from src.pipeline.orchestrator import PipelineOrchestrator


def handle_csv_upload(uploaded_file) -> None:
    if uploaded_file is None:
        return

    if not check_connection():
        st.sidebar.error("Supabase not connected. Run the migration first.")
        return

    try:
        data = uploaded_file.getvalue()
        with st.spinner("Importing reviews..."):
            result = IngestionService().ingest_csv_bytes(data)

        st.sidebar.success(
            f"Imported {result.stored} reviews "
            f"({result.skipped} skipped as duplicate/spam)"
        )
        st.session_state["last_ingestion"] = {
            "source": "csv",
            "fetched": result.fetched,
            "stored": result.stored,
            "skipped": result.skipped,
        }
        st.session_state["data_version"] = st.session_state.get("data_version", 0) + 1
    except CSVImportError as exc:
        st.sidebar.error(f"CSV import failed: {exc}")
    except SupabaseConfigurationError as exc:
        st.sidebar.error(str(exc))
    except Exception as exc:
        st.sidebar.error(f"Unexpected error during import: {exc}")


def handle_reddit_fetch() -> None:
    if not check_connection():
        st.sidebar.error("Supabase not connected. Run the migration first.")
        return

    try:
        with st.spinner("Fetching Reddit discussions..."):
            result = IngestionService().ingest_reddit()

        st.sidebar.success(
            f"Fetched {result.fetched} posts/comments, stored {result.stored} "
            f"({result.skipped} skipped)"
        )
        st.session_state["last_ingestion"] = {
            "source": "reddit",
            "fetched": result.fetched,
            "stored": result.stored,
            "skipped": result.skipped,
        }
        st.session_state["data_version"] = st.session_state.get("data_version", 0) + 1
    except RedditFetchError as exc:
        st.sidebar.error(f"Reddit fetch failed: {exc}")
    except ScrapeError as exc:
        st.sidebar.error(str(exc))
    except Exception as exc:
        st.sidebar.error(f"Reddit fetch failed: {exc}")


def handle_all_stores_fetch() -> None:
    if not check_connection():
        st.sidebar.error("Supabase not connected. Run the migration first.")
        return

    try:
        with st.sidebar.status("Fetching Play Store and App Store…", expanded=True) as status:

            def on_progress(message: str) -> None:
                status.write(message)

            result = PipelineOrchestrator().run_stores_ingestion_sync(
                progress_callback=on_progress,
            )
            status.update(
                label=f"Store fetch {result.status}",
                state="complete" if result.status != "failed" else "error",
            )

        playstore = result.sources.get("playstore")
        appstore = result.sources.get("appstore")
        if result.status == "failed":
            st.sidebar.error("Both store fetches failed.")
            for source, source_result in result.sources.items():
                if source_result.error:
                    st.sidebar.caption(f"{source}: {source_result.error}")
            return

        ps_stored = playstore.stored if playstore else 0
        as_stored = appstore.stored if appstore else 0
        ps_new = playstore.new if playstore else 0
        as_new = appstore.new if appstore else 0

        if result.status == "partial":
            st.sidebar.warning(
                f"Partial success — Play Store: {ps_stored} stored ({ps_new} new) | "
                f"App Store: {as_stored} stored ({as_new} new)"
            )
            for source, source_result in result.sources.items():
                if source_result.error:
                    st.sidebar.caption(f"{source} failed: {source_result.error}")
        else:
            st.sidebar.success(
                f"Play Store: {ps_stored} stored ({ps_new} new) | "
                f"App Store: {as_stored} stored ({as_new} new)"
            )

        st.session_state["last_ingestion"] = {
            "source": "all_stores",
            "fetched": sum(s.fetched for s in result.sources.values() if s.error is None),
            "stored": ps_stored + as_stored,
            "skipped": sum(s.skipped for s in result.sources.values() if s.error is None),
        }
        st.session_state["last_pipeline"] = {
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
            "analyzed": 0,
            "embedded": 0,
            "duration_seconds": result.duration_seconds,
        }
        st.session_state["data_version"] = st.session_state.get("data_version", 0) + 1
    except ScrapeError as exc:
        st.sidebar.error(str(exc))
    except Exception as exc:
        st.sidebar.error(f"Store fetch failed: {exc}")


def handle_appstore_fetch() -> None:
    if not check_connection():
        st.sidebar.error("Supabase not connected. Run the migration first.")
        return

    try:
        with st.spinner("Fetching App Store reviews..."):
            result = IngestionService().ingest_appstore()

        st.sidebar.success(
            f"Fetched {result.fetched} reviews, stored {result.stored} "
            f"({result.skipped} skipped)"
        )
        st.session_state["last_ingestion"] = {
            "source": "appstore",
            "fetched": result.fetched,
            "stored": result.stored,
            "skipped": result.skipped,
        }
        st.session_state["data_version"] = st.session_state.get("data_version", 0) + 1
    except ScrapeError as exc:
        st.sidebar.error(str(exc))
    except Exception as exc:
        st.sidebar.error(f"App Store fetch failed: {exc}")


def handle_playstore_fetch() -> None:
    if not check_connection():
        st.sidebar.error("Supabase not connected. Run the migration first.")
        return

    try:
        with st.spinner("Fetching Play Store reviews..."):
            result = IngestionService().ingest_playstore()

        st.sidebar.success(
            f"Fetched {result.fetched} reviews, stored {result.stored} "
            f"({result.skipped} skipped)"
        )
        st.session_state["last_ingestion"] = {
            "source": "playstore",
            "fetched": result.fetched,
            "stored": result.stored,
            "skipped": result.skipped,
        }
        st.session_state["data_version"] = st.session_state.get("data_version", 0) + 1
    except ScrapeError as exc:
        st.sidebar.error(str(exc))
    except Exception as exc:
        st.sidebar.error(f"Play Store fetch failed: {exc}")
