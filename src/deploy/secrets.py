"""Streamlit Cloud secrets bridge and configuration verification (Phase 4.5.4)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Mapping

# Keys copied from Streamlit secrets into os.environ (uppercase env names).
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

# Map Streamlit / env keys to pydantic Settings field names.
ENV_TO_SETTINGS_FIELD: dict[str, str] = {
    "SUPABASE_URL": "supabase_url",
    "SUPABASE_SERVICE_KEY": "supabase_service_key",
    "LLM_PROVIDER": "llm_provider",
    "GEMINI_API_KEY": "gemini_api_key",
    "GEMINI_MODEL": "gemini_model",
    "OPENAI_API_KEY": "openai_api_key",
    "OPENAI_MODEL": "openai_model",
    "GROQ_API_KEY": "groq_api_key",
    "GROQ_MODEL": "groq_model",
    "EMBEDDING_PROVIDER": "embedding_provider",
    "GEMINI_EMBEDDING_MODEL": "gemini_embedding_model",
    "OPENAI_EMBEDDING_MODEL": "openai_embedding_model",
    "EMBEDDING_DIMENSIONS": "embedding_dimensions",
    "REDDIT_USER_AGENT": "reddit_user_agent",
    "REDDIT_REQUEST_DELAY_SECONDS": "reddit_request_delay_seconds",
    "SPOTIFY_PLAY_STORE_APP_ID": "spotify_play_store_app_id",
    "SPOTIFY_APP_STORE_APP_ID": "spotify_app_store_app_id",
    "MIN_REVIEWS_PLAYSTORE": "min_reviews_playstore",
    "MIN_REVIEWS_APPSTORE": "min_reviews_appstore",
    "MIN_REVIEWS_REDDIT": "min_reviews_reddit",
    "ANALYSIS_BATCH_SIZE": "analysis_batch_size",
    "ANALYSIS_REQUEST_DELAY_SECONDS": "analysis_request_delay_seconds",
    "COLLECTIVE_ANALYSIS_THRESHOLD": "collective_analysis_threshold",
    "RAG_MIN_CONFIDENCE": "rag_min_confidence",
    "RAG_TOP_K": "rag_top_k",
    "RAG_MIN_SIMILARITY": "rag_min_similarity",
}

# Common aliases seen in Supabase / Streamlit Cloud examples.
ENV_ALIASES: dict[str, str] = {
    "SUPABASE_KEY": "SUPABASE_SERVICE_KEY",
    "SUPABASE_SERVICE_ROLE_KEY": "SUPABASE_SERVICE_KEY",
    "SERVICE_ROLE_KEY": "SUPABASE_SERVICE_KEY",
}

NESTED_SECRET_SECTIONS: dict[str, dict[str, str]] = {
    "supabase": {
        "url": "SUPABASE_URL",
        "SUPABASE_URL": "SUPABASE_URL",
        "service_key": "SUPABASE_SERVICE_KEY",
        "service_role_key": "SUPABASE_SERVICE_KEY",
        "key": "SUPABASE_SERVICE_KEY",
        "SUPABASE_SERVICE_KEY": "SUPABASE_SERVICE_KEY",
    },
    "groq": {
        "api_key": "GROQ_API_KEY",
        "GROQ_API_KEY": "GROQ_API_KEY",
        "model": "GROQ_MODEL",
        "GROQ_MODEL": "GROQ_MODEL",
    },
    "gemini": {
        "api_key": "GEMINI_API_KEY",
        "GEMINI_API_KEY": "GEMINI_API_KEY",
        "model": "GEMINI_MODEL",
        "GEMINI_MODEL": "GEMINI_MODEL",
        "embedding_model": "GEMINI_EMBEDDING_MODEL",
        "GEMINI_EMBEDDING_MODEL": "GEMINI_EMBEDDING_MODEL",
    },
    "reddit": {
        "user_agent": "REDDIT_USER_AGENT",
        "REDDIT_USER_AGENT": "REDDIT_USER_AGENT",
    },
}


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
    return str(value).strip().strip('"').strip("'")


def _secrets_mapping() -> Mapping[str, Any] | None:
    try:
        import streamlit as st  # noqa: PLC0415
        from streamlit.errors import StreamlitSecretNotFoundError  # noqa: PLC0415

        secrets_obj = getattr(st, "secrets", None)
        if secrets_obj is None:
            return None
        try:
            # Triggers parse; raises when no secrets.toml (local dev without secrets).
            next(iter(secrets_obj), None)
        except StreamlitSecretNotFoundError:
            return None
        return secrets_obj
    except Exception:
        return None


def _set_env(env_key: str, value: str, env_values: dict[str, str]) -> None:
    if not value:
        return
    canonical = ENV_ALIASES.get(env_key, env_key)
    if canonical not in env_values:
        env_values[canonical] = value


def collect_env_secrets() -> dict[str, str]:
    """Read flat, aliased, and nested Streamlit secrets as uppercase env keys."""
    secrets_obj = _secrets_mapping()
    if secrets_obj is None:
        return {}

    env_values: dict[str, str] = {}
    try:
        for key in STREAMLIT_SECRET_KEYS:
            if key in secrets_obj:
                _set_env(key, _coerce_secret_value(secrets_obj[key]), env_values)

        for alias, canonical in ENV_ALIASES.items():
            if alias in secrets_obj:
                _set_env(canonical, _coerce_secret_value(secrets_obj[alias]), env_values)

        for section, mapping in NESTED_SECRET_SECTIONS.items():
            if section not in secrets_obj:
                continue
            section_values = secrets_obj[section]
            if not isinstance(section_values, Mapping):
                continue
            for nested_key, env_key in mapping.items():
                if nested_key in section_values:
                    _set_env(env_key, _coerce_secret_value(section_values[nested_key]), env_values)
    except Exception:
        return env_values

    return env_values


def streamlit_secret_fields() -> dict[str, Any]:
    """Map Streamlit secrets to pydantic Settings field names."""
    fields: dict[str, Any] = {}
    for env_key, value in collect_env_secrets().items():
        field_name = ENV_TO_SETTINGS_FIELD.get(env_key)
        if field_name:
            fields[field_name] = value
    return fields


def apply_streamlit_secrets() -> int:
    """Copy ``st.secrets`` into ``os.environ`` for pydantic-settings."""
    applied = 0
    for env_key, value in collect_env_secrets().items():
        if value and not os.environ.get(env_key):
            os.environ[env_key] = value
            applied += 1
    return applied


def bootstrap_settings() -> int:
    """Apply Streamlit secrets and refresh cached Settings (call each app rerun)."""
    from app.config import clear_settings_cache  # noqa: PLC0415

    applied = apply_streamlit_secrets()
    clear_settings_cache()
    return applied


def verify_secrets(*, clear_cache: bool = True) -> SecretCheckResult:
    """Validate required configuration for production deploy."""
    if clear_cache:
        bootstrap_settings()

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

    secrets_obj = _secrets_mapping()
    if secrets_obj is not None and not present and missing:
        warnings.append(
            "Streamlit secrets loaded but SUPABASE_URL was not found — use flat keys "
            "or a [supabase] section (see .streamlit/secrets.toml.example)"
        )

    return SecretCheckResult(
        ok=len(missing) == 0,
        missing=missing,
        present=present,
        warnings=warnings,
    )
