"""Global branding and Stitch-aligned theme for Spotify Review Analyzer."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

APP_NAME = "Spotify Review Analyzer"
APP_TAGLINE = "Product Research Intelligence Platform"

_STYLES_DIR = Path(__file__).resolve().parent.parent / "styles"

SPOTIFY_LOGO_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">
  <circle cx="12" cy="12" r="12" fill="#1DB954"/>
  <path fill="#131313" d="M17.5 16.2c-.2.3-.6.4-.9.2-2.6-1.6-5.9-1.9-9.8-1.1-.4.1-.7-.2-.8-.5-.1-.4.2-.7.5-.8 4.2-.9 7.9-.6 10.8 1.2.4.2.5.6.4.9zm1.3-3.1c-.3.4-.8.6-1.2.3-3-1.8-7.5-2.4-11-1.3-.5.1-1-.1-1.1-.6-.1-.5.1-1 .6-1.1 3.9-1.2 10.4-1 14.7 1.5.5.3.7.9.4 1.3zm.1-3.2C14.9 7.9 8.1 7.7 4.4 9c-.6.2-1.2-.2-1.4-.7-.2-.6.2-1.2.7-1.4 4.2-1.2 11.1-1 15.6 1.5.5.3.7 1 .4 1.5-.3.4-1 .6-1.5.3z"/>
</svg>
"""


def inject_global_theme() -> None:
    """Inject Stitch design-system CSS on every rerun (Streamlit drops prior style tags)."""
    theme_version = "20250622i"
    css_path = _STYLES_DIR / "theme.css"
    if css_path.exists():
        st.markdown(
            f"<!-- sra-theme-{theme_version} -->\n<style>{css_path.read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True,
        )


def render_sidebar_branding() -> None:
    """Logo, app name, and tagline — first block in the sidebar."""
    st.sidebar.markdown(
        f"""
        <div class="sra-brand-wrap">
          <div class="sra-brand-logo">{SPOTIFY_LOGO_SVG}</div>
          <div>
            <p class="sra-brand-title">{APP_NAME}</p>
            <p class="sra-brand-tagline">{APP_TAGLINE}</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_page_links(pages: list) -> None:
    """Custom page navigation rendered below branding (default nav is hidden)."""
    for page in pages:
        st.sidebar.page_link(page, use_container_width=True)


def render_page_header(title: str, subtitle: str | None = None) -> None:
    """Consistent page title block across all dashboards."""
    subtitle_html = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div class="sra-page-header">
          <h1>{title}</h1>
          {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_panel(title: str, body_html: str, *, ai_accent: bool = False) -> None:
    """Styled content panel matching Stitch cards."""
    panel_class = "sra-panel-ai" if ai_accent else "sra-panel"
    st.markdown(
        f"""
        <div class="{panel_class}">
          <p class="sra-panel-title">{title}</p>
          <div style="color: #e5e2e1; font-size: 0.95rem; line-height: 1.5;">{body_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_title(title: str) -> None:
    st.markdown(f'<p class="sra-panel-title" style="margin-top:1rem;">{title}</p>', unsafe_allow_html=True)
