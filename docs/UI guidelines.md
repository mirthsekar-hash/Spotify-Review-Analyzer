# Spotify Review Analyzer — UI Guidelines

Reference designs: `docs/stitch_spotify_review_discovery_engine (2)/stitch_spotify_review_discovery_engine/` (`DESIGN.md` + per-screen `code.html`).

## Branding

1. **Spotify logo** — Green circle logo in the sidebar brand block (`render_sidebar_branding()`).
2. **App name** — Display **Spotify Review Analyzer** everywhere (not Review Engine / Discovery Engine).
3. **Tagline** — "Product Research Intelligence Platform" under the app name in the sidebar.

## Design system

4. **Spotify-like dark theme** — Use shared tokens from `app/styles/theme.css`:
   - Background `#131313`, surfaces `#201f1f`, primary `#1DB954`
   - Inter typography, 8px/12px border radius
5. **Consistent layout** — All pages use `render_page_header()` and `render_section_title()` from `app/components/branding.py`.
6. **Components** — KPI cards, status strip, chips, panels, and Plotly charts follow Stitch styling via `theme.css` and `chart_theme.py`.

## Copy & messaging

7. **No subscription/plan upsell** — This is a review analysis tool, not the Spotify streaming app. Avoid "upgrade plan", "premium", or provider billing language in user-facing UI.
8. **LLM errors** — Refer to API quota or `.env` configuration, not "provider plans".

## Implementation

- Global theme injection: `inject_global_theme()` in `app/main.py`
- **Sidebar header** — Brand block first, then `st.page_link` navigation (`st.navigation(..., position="hidden")`). Default Streamlit nav is hidden so logo is never sandwiched between nav and pipeline controls.
- **Research Assistant** — Fixed Spotify-logo FAB at bottom-right of the viewport (visible while scrolling). Opens a floating chat panel docked above the button — not a centered modal. See `app/components/research_assistant_popup.py`.
- Streamlit theme: `.streamlit/config.toml`
- Page icons in navigation may use emoji; branding text must use the official app name above.
