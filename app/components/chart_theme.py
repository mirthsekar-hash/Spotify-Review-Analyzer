"""Shared Plotly dark theme aligned with Stitch DESIGN.md."""

from __future__ import annotations

PLOTLY_DARK_LAYOUT: dict = {
    "paper_bgcolor": "#131313",
    "plot_bgcolor": "#201f1f",
    "font": {"family": "Inter, sans-serif", "color": "#e5e2e1", "size": 13},
    "margin": {"t": 40, "b": 40, "l": 40, "r": 20},
    "colorway": ["#1DB954", "#509BF5", "#E91429", "#A855F7", "#B3B3B3"],
    "xaxis": {
        "gridcolor": "#2a2a2a",
        "linecolor": "#333333",
        "zerolinecolor": "#333333",
    },
    "yaxis": {
        "gridcolor": "#2a2a2a",
        "linecolor": "#333333",
        "zerolinecolor": "#333333",
    },
    "legend": {"bgcolor": "rgba(0,0,0,0)", "font": {"color": "#b3b3b3"}},
}


def apply_dark_theme(fig, **extra_layout) -> None:
    layout = dict(PLOTLY_DARK_LAYOUT)
    layout.update(extra_layout)
    fig.update_layout(**layout)
