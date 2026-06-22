"""Tests for Phase 4.5 deployment utilities."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from src.deploy.secrets import (
    STREAMLIT_SECRET_KEYS,
    SecretCheckResult,
    apply_streamlit_secrets,
    verify_secrets,
)
from src.deploy.smoke import EXPECTED_PAGES, run_smoke_test


def test_streamlit_secret_keys_include_core():
    assert "SUPABASE_URL" in STREAMLIT_SECRET_KEYS
    assert "GEMINI_API_KEY" in STREAMLIT_SECRET_KEYS
    assert "REDDIT_USER_AGENT" in STREAMLIT_SECRET_KEYS


def test_apply_streamlit_secrets_sets_env(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    fake_secrets = {"SUPABASE_URL": "https://example.supabase.co"}

    mock_st = MagicMock()
    mock_st.secrets = fake_secrets

    with patch.dict("sys.modules", {"streamlit": mock_st}):
        applied = apply_streamlit_secrets()

    assert applied >= 1
    assert os.environ.get("SUPABASE_URL") == "https://example.supabase.co"


def test_apply_streamlit_secrets_noop_without_streamlit(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    import sys

    original = sys.modules.pop("streamlit", None)
    try:
        applied = apply_streamlit_secrets()
    finally:
        if original is not None:
            sys.modules["streamlit"] = original
    assert applied == 0


def test_verify_secrets_reports_missing(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("REDDIT_USER_AGENT", "")

    from app.config import clear_settings_cache

    clear_settings_cache()
    result = verify_secrets(clear_cache=True)
    assert isinstance(result, SecretCheckResult)
    assert not result.ok
    assert "SUPABASE_URL" in result.missing


def test_smoke_test_pages_and_fallbacks_exist():
    result = run_smoke_test(skip_db=True)
    assert any("dashboard pages" in c for c in result.checks)
    assert any("Fallback CSVs" in c for c in result.checks)
    assert any("RAG stack" in c for c in result.checks)


def test_expected_page_count():
    assert len(EXPECTED_PAGES) == 9
