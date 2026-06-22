"""Configuration tests."""

from app.config import Settings, clear_settings_cache


def test_settings_loads_from_env(monkeypatch):
    clear_settings_cache()
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("REDDIT_USER_AGENT", "test-agent/1.0")

    settings = Settings(_env_file=None)
    assert settings.supabase_url == "https://example.supabase.co"
    assert settings.llm_provider == "groq"
    assert settings.groq_model == "llama-3.3-70b-versatile"
    assert settings.embedding_provider == "gemini"
    assert settings.active_llm_model() == "llama-3.3-70b-versatile"
    assert settings.is_configured()


def test_missing_required_keys(monkeypatch):
    clear_settings_cache()
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("REDDIT_USER_AGENT", raising=False)

    settings = Settings(_env_file=None)
    missing = settings.missing_required()
    assert "SUPABASE_URL" in missing
    assert "SUPABASE_SERVICE_KEY" in missing
    assert "GROQ_API_KEY" in missing
    assert "GEMINI_API_KEY" in missing
    assert "REDDIT_USER_AGENT" in missing
