"""LLM provider factory tests."""

from app.config import Settings, clear_settings_cache
from src.llm.factory import create_llm_provider
from src.llm.gemini_provider import GeminiProvider
from src.llm.groq_provider import GroqProvider
from src.llm.openai_provider import OpenAIProvider


def test_create_gemini_provider():
    settings = Settings(
        llm_provider="gemini",
        gemini_api_key="test-key",
        gemini_model="gemini-2.5-flash",
        _env_file=None,
    )
    provider = create_llm_provider(settings)
    assert isinstance(provider, GeminiProvider)


def test_create_openai_provider():
    settings = Settings(
        llm_provider="openai",
        openai_api_key="test-key",
        openai_model="gpt-4o",
        _env_file=None,
    )
    provider = create_llm_provider(settings)
    assert isinstance(provider, OpenAIProvider)


def test_create_groq_provider():
    settings = Settings(
        llm_provider="groq",
        groq_api_key="test-key",
        groq_model="llama-3.3-70b-versatile",
        _env_file=None,
    )
    provider = create_llm_provider(settings)
    assert isinstance(provider, GroqProvider)
