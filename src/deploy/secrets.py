"""Streamlit Cloud secrets bridge and configuration verification (Phase 4.5.4)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# Keys accepted from Streamlit secrets / environment (uppercase env names).
STREAMLIT_SECRET_KEYS: tuple[str, ...] = (
    "SUPABASE_URL",
    "SUPABASE_SERVICE_KEY",
    "LLM_PROVIDER",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "GROQ_API_KEY",
    "GROQ_MODEL",
    "EMBEDDING_PROVIDER",
    "GEMINI_EMBEDDING_MODEL",
    "OPENAI_EMBEDDING_MODEL",
    "EMBEDDING_DIMENSIONS",
    "REDDIT_USER_AGENT",
    "REDDIT_REQUEST_DELAY_SECONDS",
    "SPOTIFY_PLAY_STORE_APP_ID",
    "SPOTIFY_APP_STORE_APP_ID",
    "MIN_REVIEWS_PLAYSTORE",
    "MIN_REVIEWS_APPSTORE",
    "MIN_REVIEWS_REDDIT",
    "ANALYSIS_BATCH_SIZE",
    "ANALYSIS_REQUEST_DELAY_SECONDS",
    "COLLECTIVE_ANALYSIS_THRESHOLD",
    "RAG_MIN_CONFIDENCE",
    "RAG_TOP_K",
    "RAG_MIN_SIMILARITY",
)


@dataclass
class SecretCheckResult:
    ok: bool
    missing: list[str] = field(default_factory=list)
    present: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = []
        if self.ok:
            lines.append("All required secrets are configured.")
        else:
            lines.append(f"Missing required secrets: {', '.join(self.missing)}")
        if self.present:
            lines.append(f"Configured ({len(self.present)}): {', '.join(self.present)}")
        for warning in self.warnings:
            lines.append(f"Warning: {warning}")
        return "\n".join(lines)


def _coerce_secret_value(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def apply_streamlit_secrets() -> int:
    """Copy ``st.secrets`` into ``os.environ`` so pydantic-settings can read them.

    Returns the number of keys applied. Safe to call outside a Streamlit runtime.
    """
    applied = 0
    try:
        import streamlit as st  # noqa: PLC0415 — optional runtime import

        secrets_obj = getattr(st, "secrets", None)
        if secrets_obj is None:
            return 0

        for key in STREAMLIT_SECRET_KEYS:
            if key not in secrets_obj:
                continue
            value = _coerce_secret_value(secrets_obj[key])
            if value and not os.environ.get(key):
                os.environ[key] = value
                applied += 1
    except Exception:
        return applied
    return applied


def verify_secrets(*, clear_cache: bool = True) -> SecretCheckResult:
    """Validate required configuration for production deploy."""
    if clear_cache:
        from app.config import clear_settings_cache, get_settings  # noqa: PLC0415

        clear_settings_cache()
        settings = get_settings()
    else:
        from app.config import get_settings  # noqa: PLC0415

        settings = get_settings()

    missing = settings.missing_required()
    present: list[str] = []

    for key in STREAMLIT_SECRET_KEYS:
        if os.environ.get(key, "").strip():
            present.append(key)

    warnings: list[str] = []
    if settings.llm_provider == "groq" and not os.environ.get("GROQ_API_KEY", "").strip():
        if "GROQ_API_KEY" not in missing:
            missing.append("GROQ_API_KEY")

    ua = settings.reddit_user_agent.strip()
    if ua and "your@email.com" in ua:
        warnings.append("REDDIT_USER_AGENT still uses placeholder contact email")

    return SecretCheckResult(
        ok=len(missing) == 0,
        missing=missing,
        present=present,
        warnings=warnings,
    )
