"""Interview Validation dashboard — Phase 4.4."""

from __future__ import annotations

from uuid import UUID

import pandas as pd
import streamlit as st

from app.components.branding import render_page_header, render_section_title
from src.schemas.interview_insight import InterviewInsightCreate, InterviewInsightUpdate
from src.services.interview_validation_service import InterviewValidationData, InterviewValidationService

SESSION_REFRESH_KEY = "interview_validation_refresh"


@st.cache_data(ttl=30, show_spinner="Loading interview insights...")
def load_validation_data(refresh_key: int) -> InterviewValidationData:
    return InterviewValidationService().get_validation_data()


def _bump_refresh() -> None:
    st.session_state[SESSION_REFRESH_KEY] = st.session_state.get(SESSION_REFRESH_KEY, 0) + 1
    load_validation_data.clear()


def render_empty_state() -> None:
    st.info(
        "No interview insights recorded yet. Use the form above to add findings from "
        "user interviews, link them to a collective theme, and compare against review evidence."
    )
    st.markdown(
        "**How to use this page**\n"
        "1. Run collective analysis so themes exist in the database.\n"
        "2. Add interview insights from your user research sessions.\n"
        "3. Link each insight to the closest discovery theme.\n"
        "4. Enter interview validation % and confidence to compare qualitative vs. review evidence."
    )


def _theme_options(themes: list) -> dict[str, str]:
    options = {"— No linked theme —": ""}
    for theme in themes:
        options[theme.theme_name] = str(theme.id)
    return options


def _theme_label_from_id(theme_id: str | None, options: dict[str, str]) -> str:
    if not theme_id:
        return "— No linked theme —"
    for label, value in options.items():
        if value == theme_id:
            return label
    return "— No linked theme —"


def render_insight_form(data: InterviewValidationData, *, edit_id: UUID | None = None) -> None:
    service = InterviewValidationService()
    options = _theme_options(data.themes)
    labels = list(options.keys())

    existing = None
    if edit_id:
        existing = next((row for row in data.insights if row.id == edit_id), None)

    title = "Edit interview insight" if edit_id else "Add interview insight"
    with st.form(f"interview_insight_form_{edit_id or 'new'}", clear_on_submit=not edit_id):
        st.markdown(f"**{title}**")
        insight_text = st.text_area(
            "Insight",
            value=existing.insight if existing else "",
            placeholder="e.g. Users say Discover Weekly feels repetitive after two weeks",
            height=100,
        )

        default_theme = _theme_label_from_id(
            str(existing.linked_theme_id) if existing and existing.linked_theme_id else None,
            options,
        )
        theme_label = st.selectbox(
            "Linked theme",
            options=labels,
            index=labels.index(default_theme) if default_theme in labels else 0,
            help="Connect this interview finding to a collective theme for review evidence comparison.",
        )

        col_val, col_conf = st.columns(2)
        with col_val:
            validation_pct = st.number_input(
                "Interview validation %",
                min_value=0.0,
                max_value=100.0,
                value=float(existing.validation_pct) if existing and existing.validation_pct is not None else 0.0,
                step=5.0,
                help="How strongly interviews support this insight (0–100).",
            )
        with col_conf:
            default_confidence = (
                float(existing.confidence_score)
                if existing and existing.confidence_score is not None
                else 0.0
            )
            confidence_score = st.number_input(
                "Confidence score",
                min_value=0.0,
                max_value=1.0,
                value=default_confidence,
                step=0.05,
                format="%.2f",
                help="Overall confidence (0–1). Leave at 0 to auto-compute from validation % and evidence.",
            )

        notes = st.text_area(
            "Notes",
            value=existing.notes if existing and existing.notes else "",
            placeholder="Session ID, participant segment, quotes, etc.",
            height=80,
        )

        submitted = st.form_submit_button(
            "Save changes" if edit_id else "Add insight",
            type="primary",
            use_container_width=True,
        )

        if submitted:
            if not insight_text.strip():
                st.error("Insight text is required.")
                return

            theme_id_str = options.get(theme_label) or None
            linked_theme_id = UUID(theme_id_str) if theme_id_str else None
            use_confidence = confidence_score if confidence_score > 0 else None

            try:
                if edit_id:
                    service.update_insight(
                        edit_id,
                        InterviewInsightUpdate(
                            insight=insight_text.strip(),
                            linked_theme_id=linked_theme_id,
                            validation_pct=validation_pct,
                            confidence_score=use_confidence,
                            notes=notes.strip() or None,
                        ),
                    )
                    st.success("Interview insight updated.")
                else:
                    service.create_insight(
                        InterviewInsightCreate(
                            insight=insight_text.strip(),
                            linked_theme_id=linked_theme_id,
                            validation_pct=validation_pct,
                            confidence_score=use_confidence,
                            notes=notes.strip() or None,
                        )
                    )
                    st.success("Interview insight added.")
                _bump_refresh()
                st.rerun()
            except Exception as exc:
                st.error(f"Could not save insight: {exc}")


def render_comparison_table(data: InterviewValidationData) -> None:
    rows = []
    for item in data.insights:
        theme_label = item.linked_theme_name or "—"
        evidence = (
            f"{item.review_evidence_count} reviews"
            if item.linked_theme_id
            else "No theme linked"
        )
        validation = f"{item.validation_pct:.0f}%" if item.validation_pct is not None else "—"
        confidence = f"{item.confidence_score:.2f}" if item.confidence_score is not None else "—"
        rows.append(
            {
                "Insight": item.insight,
                "Linked theme": theme_label,
                "Review evidence": evidence,
                "Interview validation %": validation,
                "Confidence score": confidence,
                "Notes": item.notes or "—",
            }
        )

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_edit_panel(data: InterviewValidationData) -> None:
    if not data.insights:
        return

    render_section_title("Edit or delete")
    options = {row.insight[:80] + ("…" if len(row.insight) > 80 else ""): row.id for row in data.insights}
    selected_label = st.selectbox("Select insight to edit", options=list(options.keys()))
    selected_id = options[selected_label]

    render_insight_form(data, edit_id=selected_id)

    if st.button("Delete selected insight", type="secondary"):
        try:
            InterviewValidationService().delete_insight(selected_id)
            st.success("Interview insight deleted.")
            _bump_refresh()
            st.rerun()
        except Exception as exc:
            st.error(f"Could not delete insight: {exc}")


def main() -> None:
    render_page_header(
        "Part 2 — User Research Validation",
        "Compare qualitative interview findings with review evidence from collective themes.",
    )

    refresh_key = st.session_state.get(SESSION_REFRESH_KEY, 0)
    data = load_validation_data(refresh_key)

    if not data.db_connected:
        st.error("Cannot connect to Supabase. Check your database configuration.")
        return

    if not data.themes:
        st.warning(
            "No collective themes available yet. Run **Re-run Collective Analysis** in the sidebar "
            "before linking interview insights to review evidence."
        )

    render_insight_form(data)

    st.divider()
    render_section_title("Interview vs. review evidence")

    if not data.insights:
        render_empty_state()
    else:
        render_comparison_table(data)
        st.caption(
            f"{len(data.insights)} interview insight(s) · "
            "Review evidence counts come from linked theme review mappings."
        )
        render_edit_panel(data)


main()
